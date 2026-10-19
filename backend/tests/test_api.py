import io
import base64
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import wave
import av

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import main
from fastapi.testclient import TestClient


def wav_bytes():
    stream = io.BytesIO()
    with wave.open(stream, 'wb') as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(16000)
        audio.writeframes(b'\0\0' * 16000)
    return stream.getvalue()


def mp3_with_cover_bytes():
    output = io.BytesIO()
    with av.open(output, 'w', format='mp3') as container:
        stream = container.add_stream('libmp3lame', rate=16000)
        stream.layout = 'mono'
        frame = av.AudioFrame(format='s16p', layout='mono', samples=16000)
        frame.sample_rate = 16000
        frame.planes[0].update(bytes(frame.planes[0].buffer_size))
        for packet in stream.encode(frame):
            container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)
    encoded = output.getvalue()
    if encoded[:3] == b'ID3':
        size = sum(value << (7*(3-index)) for index,value in enumerate(encoded[6:10]))
        encoded = encoded[10+size:]
    # Real ID3v2 APIC metadata: FFmpeg exposes this PNG as attached_pic video.
    cover = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl6l9sAAAAASUVORK5CYII=')
    picture = b'\0image/png\0\x03\0' + cover
    frame = b'APIC' + len(picture).to_bytes(4,'big') + b'\0\0' + picture
    size = bytes((len(frame) >> shift) & 0x7f for shift in [21,14,7,0])
    return b'ID3\x03\0\0' + size + frame + encoded


class APITest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data_patch = patch.object(main, 'DATA', Path(self.tmp.name))
        self.data_patch.start()
        self.client = TestClient(main.app)
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.data_patch.stop()
        self.tmp.cleanup()

    def upload(self):
        result = self.client.post('/api/jobs', files={'file': ('sample.wav', wav_bytes(), 'audio/wav')})
        self.assertEqual(result.status_code, 201, result.text)
        return result.json()

    def test_upload_media_and_delete(self):
        job = self.upload()
        self.assertNotIn('path', job)
        self.assertEqual(job['kind'], 'audio')
        self.assertEqual(job['asl_status'], 'not_available')
        self.assertEqual(self.client.get(f"/api/jobs/{job['id']}/media").content, wav_bytes())
        self.assertEqual(len(self.client.get('/api/jobs').json()), 1)
        self.assertEqual(self.client.delete(f"/api/jobs/{job['id']}").status_code, 204)
        self.assertEqual(self.client.get(f"/api/jobs/{job['id']}").status_code, 404)
        self.assertFalse(list(Path(self.tmp.name).glob('*.wav')))

    def test_mp3_album_cover_remains_audio(self):
        content = mp3_with_cover_bytes()
        with av.open(io.BytesIO(content)) as media:
            self.assertTrue(media.streams.audio)
            self.assertTrue(media.streams.video, 'Fixture must reproduce the cover-art stream')
            self.assertTrue(media.streams.video[0].disposition & av.stream.Disposition.attached_pic)
            self.assertEqual(main.media_kind(media, '.mp3'), 'audio')
            self.assertEqual(main.media_kind(media, '.mp4'), 'audio', 'Attached pictures alone never make moving video')
        result = self.client.post('/api/jobs', files={'file': ('covered.mp3', content, 'audio/mpeg')})
        self.assertEqual(result.status_code, 201, result.text)
        self.assertEqual(result.json()['kind'], 'audio')
        self.assertGreater(result.json()['duration'], .9)
        self.assertEqual(self.client.get(f"/api/jobs/{result.json()['id']}/media").content, content)
        with main.connect() as db:
            db.execute("UPDATE jobs SET kind='video' WHERE id=?", (result.json()['id'],))
        self.assertEqual(self.client.get(f"/api/jobs/{result.json()['id']}").json()['kind'], 'audio', 'Previously uploaded MP3s also get corrected metadata')
        with main.connect() as db:
            self.assertEqual(db.execute('SELECT kind FROM jobs WHERE id=?',(result.json()['id'],)).fetchone()['kind'], 'video', 'Reading corrected metadata does not rewrite saved history')

    def test_real_video_track_and_audio_extension_fallback(self):
        media = SimpleNamespace(streams=SimpleNamespace(video=[SimpleNamespace(disposition=av.stream.Disposition(0))]))
        self.assertEqual(main.media_kind(media, '.mp4'), 'video')
        self.assertEqual(main.media_kind(media, '.webm'), 'video')
        self.assertEqual(main.media_kind(media, '.MP3'), 'audio', 'Audio extensions retain the audio player with unusual metadata')

    def test_invalid_files_and_size_are_rejected(self):
        for name, content, code in [('bad.exe', b'abc', 415), ('empty.wav', b'', 400), ('fake.wav', b'not audio', 422)]:
            self.assertEqual(self.client.post('/api/jobs', files={'file': (name, content)}).status_code, code)
        with patch.object(main, 'MAX_BYTES', 8):
            self.assertEqual(self.client.post('/api/jobs', files={'file': ('large.wav', wav_bytes())}).status_code, 413)
        self.assertEqual(self.client.get('/api/jobs').json(), [])
        self.assertFalse(list(Path(self.tmp.name).glob('*.wav')))

    def test_duration_limit(self):
        with patch.object(main, 'MAX_SECONDS', 0.5):
            self.assertEqual(self.client.post('/api/jobs', files={'file': ('long.wav', wav_bytes())}).status_code, 413)

    def test_missing_model_is_explicit(self):
        job = self.upload()
        with patch.object(main, 'model_ready', return_value=False):
            self.assertEqual(self.client.post(f"/api/jobs/{job['id']}/transcribe").status_code, 503)
        self.assertEqual(self.client.get(f"/api/jobs/{job['id']}/subtitles").status_code, 409)

    def test_transcription_and_export(self):
        job = self.upload()
        segments = [{'start':0.0,'end':0.9,'text':'Hello world.','needs_review':False,'words':[]}]
        with patch.object(main, 'model_ready', return_value=True), patch.object(main, 'model', object()), patch.object(main,'loaded_profile','accurate'), patch.object(main.asr,'run_pipeline',return_value=(segments,{'processed_seconds':1})):
            self.assertEqual(self.client.post(f"/api/jobs/{job['id']}/transcribe").status_code, 202)
        result = self.client.get(f"/api/jobs/{job['id']}").json()
        self.assertEqual(result['status'], 'ready')
        self.assertEqual(result['segments'][0]['text'], 'Hello world.')
        self.assertFalse(result['segments'][0]['needs_review'])
        self.assertIn('00:00:00,000 --> 00:00:00,900', self.client.get(f"/api/jobs/{job['id']}/subtitles").text)
        self.assertTrue(self.client.get(f"/api/jobs/{job['id']}/subtitles?format=vtt").text.startswith('WEBVTT'))
        self.assertEqual(self.client.get(f"/api/jobs/{job['id']}/subtitles?format=txt").text, 'Hello world.')
        self.assertEqual(self.client.get(f"/api/jobs/{job['id']}/subtitles?format=exe").status_code, 400)

    def test_busy_job_cannot_be_deleted_or_double_started(self):
        job = self.upload()
        with main.connect() as db:
            db.execute("UPDATE jobs SET status='processing' WHERE id=?", (job['id'],))
        self.assertEqual(self.client.delete(f"/api/jobs/{job['id']}").status_code, 409)
        with patch.object(main, 'model_ready', return_value=True):
            self.assertEqual(self.client.post(f"/api/jobs/{job['id']}/transcribe").status_code, 409)

    def test_worker_failure_and_restart_recovery(self):
        job = self.upload()
        with patch.object(main, 'model_ready', return_value=True), patch.object(main, 'model', object()), patch.object(main,'loaded_profile','accurate'), patch.object(main.asr,'run_pipeline',side_effect=RuntimeError('failure')), patch.object(main.logger, 'exception'):
            self.client.post(f"/api/jobs/{job['id']}/transcribe")
        self.assertEqual(self.client.get(f"/api/jobs/{job['id']}").json()['status'], 'failed')
        with main.connect() as db:
            db.execute("UPDATE jobs SET status='queued' WHERE id=?", (job['id'],))
        main.init_db()
        self.assertEqual(self.client.get(f"/api/jobs/{job['id']}").json()['status'], 'failed')

    def test_timestamps_round_correctly(self):
        self.assertEqual(main.timestamp(59.9999), '00:01:00,000')
        self.assertEqual(main.timestamp(3661.25, '.'), '01:01:01.250')

    def test_edit_revision_and_restore(self):
        job = self.upload()
        payload = {'revision':0,'segments':[{'start':0,'end':.9,'text':'Corrected text.'}]}
        result = self.client.put(f"/api/jobs/{job['id']}/transcript",json=payload)
        self.assertEqual(result.status_code,200,result.text)
        self.assertTrue(result.json()['segments'][0]['edited'])
        self.assertTrue(result.json()['report']['audit_stale'])
        self.assertEqual(self.client.put(f"/api/jobs/{job['id']}/transcript",json=payload).status_code,409)
        payload['revision']=1
        payload['segments'][0]['text']='Second version.'
        self.assertEqual(self.client.put(f"/api/jobs/{job['id']}/transcript",json=payload).status_code,200)
        versions=self.client.get(f"/api/jobs/{job['id']}/revisions").json()
        self.assertEqual(len(versions),1)
        restored=self.client.post(f"/api/jobs/{job['id']}/revisions/{versions[0]['id']}/restore").json()
        self.assertEqual(restored['segments'][0]['text'],'Corrected text.')

    def test_reject_invalid_edit_and_profiles(self):
        job=self.upload()
        url=f"/api/jobs/{job['id']}"
        for segments in [[{'start':.5,'end':.1,'text':'bad'}],[{'start':0,'end':.9,'text':'  '}],
                         [{'start':0,'end':.8,'text':'a'},{'start':.3,'end':.9,'text':'b'}]]:
            self.assertEqual(self.client.put(url+'/transcript',json={'revision':0,'segments':segments}).status_code,422)
        self.assertEqual(self.client.post(url+'/transcribe',json={'profile':'invented'}).status_code,422)
        self.assertEqual(self.client.post(url+'/cancel').status_code,409)

    def test_cancel_retains_partial_result(self):
        job=self.upload()
        def pipeline(model,path,mode,progress,cancelled):
            progress('transcribing',40,[{'start':0,'end':.8,'text':'Partial.','needs_review':True}],{})
            main.cancel_events[job['id']].set()
            raise main.asr.Cancelled()
        with patch.object(main,'model_ready',return_value=True),patch.object(main,'model',object()),patch.object(main,'loaded_profile','accurate'),patch.object(main.asr,'run_pipeline',side_effect=pipeline):
            self.client.post(f"/api/jobs/{job['id']}/transcribe")
        result=self.client.get(f"/api/jobs/{job['id']}").json()
        self.assertEqual(result['status'],'cancelled')
        self.assertEqual(result['segments'][0]['text'],'Partial.')


if __name__ == '__main__':
    unittest.main()
