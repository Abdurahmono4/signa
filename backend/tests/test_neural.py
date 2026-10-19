import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import neural


class NeuralPlanTests(unittest.TestCase):
    def row(self):
        return {'id': 'abc', 'revision': 1, 'duration': 10.,
                'segments': json.dumps([{'start': 1., 'end': 3., 'text': 'Please open the book.'},
                                        {'start': 5., 'end': 7., 'text': 'Thank you.'}])}

    def test_continuous_motion_and_media_are_not_truncated(self):
        row = self.row()
        segments = neural.chunks(json.loads(row['segments']))
        plan = neural.build_plan(row, segments, [{'id': '0', 'duration': 5.},
                                                {'id': '1', 'duration': 1.}], 'key')
        self.assertEqual(plan['mode'], 'neural_asl')
        self.assertEqual(plan['spelled_words'], 0)
        self.assertEqual(plan['playable_signs'], 2)
        self.assertEqual(plan['playback_duration'], 12.)
        self.assertEqual(plan['hold_duration'], 2.)
        self.assertEqual(plan['items'][-1]['media_play_end'], 10.)
        clips = [item for item in plan['items'] if item['clip']]
        self.assertEqual(clips[0]['playback_rate'], 1.25)
        self.assertEqual(clips[0]['duration'], 4.)
        self.assertEqual(clips[0]['clip_end'], 5.)
        self.assertIn('/neural/motions/0?key=key', clips[0]['clip']['neural_asset'])
        for previous, following in zip(plan['items'], plan['items'][1:]):
            self.assertEqual(previous['playback_end'], following['playback_start'])
            self.assertEqual(previous['media_play_end'], following['media_play_start'])

    def test_long_input_is_split_without_losing_text(self):
        text = ' '.join(f'word{i}' for i in range(97))
        chunks = neural.chunks([{'start': 2., 'end': 42., 'text': text}])
        self.assertEqual(' '.join(item['text'] for item in chunks), text)
        self.assertEqual([len(item['text'].split()) for item in chunks], [40, 40, 17])
        self.assertEqual(chunks[0]['start'], 2.)
        self.assertEqual(chunks[-1]['end'], 42.)
        self.assertEqual(chunks[0]['end'], chunks[1]['start'])

    def test_missing_motion_fails_instead_of_emitting_idle_translation(self):
        row = self.row()
        with self.assertRaises(ValueError):
            neural.build_plan(row, neural.chunks(json.loads(row['segments'])),
                              [{'id': '0', 'duration': 2.}], 'key')

    def test_revision_and_text_changes_invalidate_cache(self):
        row = self.row()
        original = neural.key_for(row)
        row['revision'] += 1
        self.assertNotEqual(original, neural.key_for(row))
        row['revision'] -= 1
        row['segments'] = '[]'
        self.assertNotEqual(original, neural.key_for(row))

    def test_speech_pauses_keep_sentence_inputs_separate(self):
        chunks = neural.chunks([{'start': 0., 'end': 6., 'text': 'Welcome to class Every student can learn',
            'words': [{'word': 'Welcome', 'start': 0., 'end': .5},
                      {'word': 'to', 'start': .5, 'end': .7},
                      {'word': 'class', 'start': .7, 'end': 1.2},
                      {'word': 'Every', 'start': 2., 'end': 2.5},
                      {'word': 'student', 'start': 2.5, 'end': 3.2},
                      {'word': 'can', 'start': 3.2, 'end': 3.5},
                      {'word': 'learn', 'start': 3.5, 'end': 4.2}]}])
        self.assertEqual([item['text'] for item in chunks], ['Welcome to class', 'Every student can learn'])
        self.assertEqual(chunks[0]['end'], 1.2)
        self.assertEqual(chunks[1]['start'], 2.)


if __name__ == '__main__':
    unittest.main()
