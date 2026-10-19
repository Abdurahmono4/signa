from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch
import wave
import json
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import asr


class ASRTest(unittest.TestCase):
    def test_all_duration_including_tail_is_scheduled(self):
        for duration in [.1,24,24.001,70.24,124.12,1200]:
            items=asr.windows(duration)
            self.assertEqual(items[0].core_start,0)
            self.assertEqual(items[-1].core_end,duration)
            self.assertAlmostEqual(sum(w.core_end-w.core_start for w in items),duration)
            for a,b in zip(items,items[1:]):
                self.assertEqual(a.core_end,b.core_start)
                self.assertGreater(a.end,b.start)
            self.assertTrue(all(w.end-w.start<=30.00001 for w in items))

    def test_seam_words_owned_once_and_repetitions_kept(self):
        # Both windows hear the seam word; only the right core owns its midpoint.
        model=NS(transcribe=lambda *a,**kw:(iter([NS(avg_logprob=-.2,words=[NS(start=23.8,end=24.2,word=' seam',probability=.9)])]),None))
        left=asr.recognize(model,np.ones(27*asr.RATE,dtype=np.float32)*.1,0,0,24,'left')
        right=asr.recognize(model,np.ones(27*asr.RATE,dtype=np.float32)*.1,0,24,48,'right')
        self.assertEqual(len(left+right),1)
        w={'start':0,'end':.4,'word':' no','probability':.9,'source':'one','needs_review':False}
        repeated=[w,{**w,'start':.5,'end':.9}]
        self.assertEqual(len(asr.deduplicate(repeated)),2)
        self.assertEqual(len(asr.deduplicate([w,{**w,'source':'two'}])),1)

    def test_vad_does_not_remove_any_audio(self):
        calls=[]
        def transcribe(audio,**options):
            calls.append((len(audio),options))
            return iter([]),None
        signal=np.ones(50*asr.RATE,dtype=np.float32)*.02
        with patch.object(asr,'decode_timeline',return_value=(signal,{})),patch.object(asr,'activity_intervals',return_value=[]):
            result,report=asr.run_pipeline(NS(transcribe=transcribe),'unused')
        self.assertEqual(len(calls),3)
        self.assertTrue(all(not opts['vad_filter'] and opts['no_speech_threshold'] is None and opts['word_timestamps'] for _,opts in calls))
        self.assertEqual(report['processed_seconds'],50)
        self.assertEqual(report['word_count'],0)
        self.assertTrue(report['warnings'])

    def test_gap_audit_detects_missing_tail_not_silence(self):
        gaps=asr.find_gaps([(0,5),(10,15)],[{'start':0,'end':5}],20)
        self.assertEqual(gaps[0]['start'],10)
        self.assertEqual(gaps[0]['end'],15)
        self.assertEqual(asr.find_gaps([],[],20),[])

    def test_retry_is_bounded_and_cancel_checked(self):
        signal=np.ones(160*asr.RATE,dtype=np.float32)*.1
        with patch.object(asr,'decode_timeline',return_value=(signal,{})),patch.object(asr,'activity_intervals',return_value=[(0,160)]):
            result,report=asr.run_pipeline(NS(transcribe=lambda *a,**kw:(iter([]),None)),'unused')
            self.assertEqual(report['retry_count'],6)
            self.assertTrue(report['suspect_spans'])
            with self.assertRaises(asr.Cancelled):
                asr.run_pipeline(None,'unused',cancelled=lambda:True)

    def test_decode_quiet_audio_keeps_duration(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'quiet.wav'
            signal=(np.sin(np.arange(asr.RATE*2)*.05)*80).astype(np.int16)
            with wave.open(str(path),'wb') as out:
                out.setnchannels(1);out.setsampwidth(2);out.setframerate(asr.RATE);out.writeframes(signal.tobytes())
            decoded,report=asr.decode_timeline(path)
            self.assertEqual(len(decoded),asr.RATE*2)
            self.assertEqual(report['timeline_seconds'],2)
            self.assertGreater(np.max(np.abs(asr.normalize(decoded))),np.max(np.abs(decoded)))

    def test_grouping_preserves_every_word(self):
        words=[{'start':i,'end':i+.7,'word':f' word{i}','needs_review':False} for i in range(70)]
        segments=asr.group_words(words)
        self.assertEqual(' '.join(s['text'] for s in segments),' '.join(f'word{i}' for i in range(70)))

    def test_numpy_model_values_are_json_serializable(self):
        model=NS(transcribe=lambda *a,**kw:(iter([NS(avg_logprob=np.float32(-.2),words=[NS(start=np.float32(.1),end=np.float32(.5),word=' hello',probability=np.float32(.9))])]),None))
        words=asr.recognize(model,np.ones(asr.RATE,dtype=np.float32)*.1,0,0,1,'one')
        json.dumps(asr.group_words(words))


if __name__=='__main__':unittest.main()
