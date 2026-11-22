"""Verify the human-signer MP4 workflow using the English public demo as actual ASR input."""
import argparse
import json
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

import av
import httpx
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from backend.app.core import binary, probe
from backend.app.translation import normalize


def wait_for(client, job, expected):
    deadline = time.monotonic() + 240
    while time.monotonic() < deadline:
        status = client.get('/api/jobs/' + job).raise_for_status().json()
        if status['status'] == expected:
            return status
        if status['status'] in ('failed', 'cancelled'):
            raise RuntimeError(status.get('error') or status['status'])
        time.sleep(.5)
    raise TimeoutError(expected)


def audio(path, ffmpeg):
    data = subprocess.check_output([ffmpeg, '-v', 'error', '-i', str(path), '-map', '0:a:0',
                                    '-ac', '1', '-ar', '16000', '-f', 'f32le', 'pipe:1'])
    return np.frombuffer(data, np.float32).astype(np.float64)


def run(source, output, server):
    ffmpeg = binary('ffmpeg')
    with tempfile.TemporaryDirectory() as scratch, httpx.Client(base_url=server, timeout=60) as client:
        sample = Path(scratch) / 'english-real-auto.mp4'
        # Preserve elementary media streams but bypass byte-based transcript/MP4 reuse.
        subprocess.run([ffmpeg, '-v', 'error', '-i', str(source), '-map', '0:v:0', '-map', '0:a:0',
                        '-c', 'copy', '-metadata', 'comment=realignment-smoke-' + uuid.uuid4().hex,
                        str(sample)], check=True)
        with sample.open('rb') as stream:
            job = client.post('/api/upload', files={'file': (sample.name, stream, 'video/mp4')}).raise_for_status().json()['id']
        start = time.perf_counter()
        client.post('/api/jobs', json={'job_id': job, 'language': 'en', 'model': 'small'}).raise_for_status()
        status = wait_for(client, job, 'ready')
        asr_elapsed = time.perf_counter() - start
        speech = ' '.join(s['text'] for s in status['segments'])
        items = status['translation']['items']
        if (normalize(speech) != 'at least in a physical way' or len(items) != 1
                or not items[0]['supported'] or items[0].get('timing_source') != 'manual_realignment'):
            raise ValueError(f'Unexpected ASR or source plan for job {job}: {speech} {items}')
        item = items[0]
        client.get(item['video_url']).raise_for_status()
        start = time.perf_counter()
        session = client.post(f'/api/jobs/{job}/render/start', json={
            'engine': 'human', 'native_human': True, 'resolution': 720, 'subtitles': True,
            'layout': 'side_by_side', 'size': .30, 'removeGreen': True,
        }).raise_for_status().json()
        if session.get('mode') != 'native':
            raise ValueError(f'Wrong render mode: {session}')
        completed = wait_for(client, job, 'done')
        elapsed = time.perf_counter() - start
        if completed['result_token'] != session['token']:
            raise ValueError('Export ownership changed')
        download = f'/api/jobs/{job}/download?v={session["token"]}'
        target = output / 'tuzatilgan-tarjimon.mp4'
        target.write_bytes(client.get(download).raise_for_status().content)
        streams = probe(target)['streams']
        if [s['codec_name'] for s in streams] != ['h264', 'aac']:
            raise ValueError('Missing H.264 or AAC')
        if abs(float(probe(target)['format']['duration']) - status['duration']) > .1:
            raise ValueError('Original video duration changed')
        subprocess.run([ffmpeg, '-v', 'error', '-xerror', '-i', str(target), '-f', 'null', '-'], check=True)
        x, y = audio(sample, ffmpeg), audio(target, ffmpeg)
        n = min(len(x), len(y))
        correlation = float(np.dot(x[:n], y[:n]) / (np.linalg.norm(x[:n]) * np.linalg.norm(y[:n])))
        if not .95 < correlation <= 1.000001:
            raise ValueError('Original audio waveform was not retained')
        with av.open(str(target)) as movie:
            panels = [f.to_ndarray(format='rgb24')[110:510, 930:1230:2].astype('float32') for f in movie.decode(video=0)]
        movement = float(np.mean(np.abs(panels[len(panels)//4] - panels[len(panels)*3//4])))
        if movement < 1:
            raise ValueError('No measurable signer movement in output panel')
        report = {'job_id': job, 'download': download, 'input': source.name, 'asr_model': 'small',
                  'transcript': speech, 'speech_seconds': [[s['start'], s['end']] for s in status['segments']],
                  'matched_recording': item, 'human_crop_seconds': item['duration_ms'] / 1000,
                  'render_fps': streams[0]['avg_frame_rate'], 'decoded_video_frames': len(panels),
                  'source_duration': status['duration'], 'output_duration': float(probe(target)['format']['duration']),
                  'codecs': ['h264', 'aac'], 'resolution': [streams[0]['width'], streams[0]['height']],
                  'original_audio_correlation_16k_mono': correlation, 'panel_RGB_mean_abs_change': movement,
                  'asr_and_lookup_elapsed_seconds': round(asr_elapsed, 2), 'render_elapsed_seconds': round(elapsed, 2),
                  'linguistic_comprehension': 'unmeasured'}
        (output / 'eksport-sinovi.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(report, ensure_ascii=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--server', default='http://127.0.0.1:8001')
    args = parser.parse_args()
    run(args.source, args.output, args.server)
