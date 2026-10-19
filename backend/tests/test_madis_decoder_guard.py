"""Raw model boundary tests, independent of torch and downloaded weights."""
import builtins
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch


class MaDiSDecoderGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = Path(__file__).resolve().parents[1] / 'app' / 'inference' / 'madis_runner.py'
        spec = importlib.util.spec_from_file_location('signa_decoder_guard_test', source)
        cls.runner = importlib.util.module_from_spec(spec)
        original_import = builtins.__import__

        def without_torch(name, *args, **kwargs):
            if name == 'torch' or name.startswith('torch.'):
                raise AssertionError('Decoder boundary tests must not import torch.')
            return original_import(name, *args, **kwargs)

        with patch('builtins.__import__', side_effect=without_torch):
            spec.loader.exec_module(cls.runner)

    def setUp(self):
        # Each part has a separate embedding-ID range. 0 stands for PAD/EOS;
        # the adjacent IDs stand for non-codebook part tokens, not code zero.
        self.valid = {'body': {10, 11}, 'left_hand': {20, 21}, 'right_hand': {30, 31}}
        self.rows = {'body': [10, 11, 0], 'left_hand': [20, 0, 0], 'right_hand': [31, 30, 0]}

    def test_actual_codebook_entries_in_every_part_pass_without_altering_ids(self):
        before = {part: list(ids) for part, ids in self.rows.items()}
        self.assertEqual(self.runner.require_motion_tokens(self.rows, self.valid),
                         {'body': 2, 'left_hand': 1, 'right_hand': 2})
        self.assertEqual(self.rows, before)
        self.assertEqual(self.runner.DECODER_GUARD, 'nonempty-motion-token-v2')

    def test_pad_eos_mask_text_and_non_codebook_part_tokens_cannot_become_motion(self):
        self.rows['body'] = [0, 0, 1, 2, 12, 13, 14, 20, 999]
        with self.assertRaisesRegex(ValueError, 'body'):
            self.runner.require_motion_tokens(self.rows, self.valid)

    def test_each_hand_must_have_its_own_actual_codebook_entry(self):
        for part in ('left_hand', 'right_hand'):
            with self.subTest(part=part):
                rows = dict(self.rows)
                rows[part] = [0, 10, 999]
                with self.assertRaisesRegex(ValueError, part):
                    self.runner.require_motion_tokens(rows, self.valid)

    def test_missing_and_empty_streams_fail_before_decode(self):
        for value in (None, []):
            rows = dict(self.rows)
            if value is None:
                del rows['body']
            else:
                rows['body'] = value
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'body'):
                self.runner.require_motion_tokens(rows, self.valid)

    def test_covered_original_case_is_preserved_and_missing_terminal_period_is_added(self):
        encoded = {'Please open your book.': [1, 2, 3]}
        text, changes = self.runner.prepare_model_input(
            'Please open your book', encoded.__getitem__, {1, 2, 3})
        self.assertEqual(text, 'Please open your book.')
        self.assertEqual(changes, ['terminal_punctuation'])
        text, changes = self.runner.prepare_model_input(
            'Please open your book.', encoded.__getitem__, {1, 2, 3})
        self.assertEqual(text, 'Please open your book.')
        self.assertEqual(changes, [])

    def test_case_fallback_requires_complete_lowercase_coverage_and_keeps_words(self):
        encoded = {'Welcome Please read.': [1, 999, 3],
                   'welcome please read.': [1, 2, 3]}
        text, changes = self.runner.prepare_model_input(
            'Welcome Please read', encoded.__getitem__, {1, 2, 3})
        self.assertEqual(text, 'welcome please read.')
        self.assertEqual(changes, ['terminal_punctuation', 'lowercase_for_compact_vocabulary'])

    def test_unsupported_original_and_lowercase_both_fail_before_mapping_to_eos(self):
        encoded = {'Unmapped word.': [1, 999], 'unmapped word.': [1, 998]}
        with self.assertRaisesRegex(ValueError, 'Unsupported text tokens'):
            self.runner.prepare_model_input('Unmapped word.', encoded.__getitem__, {1, 2, 3})

    def test_existing_question_or_exclamation_mark_is_preserved(self):
        for caption in ('Are you ready?', 'Read it!'):
            with self.subTest(caption=caption):
                text, changes = self.runner.prepare_model_input(caption, lambda text: [1], {1})
                self.assertEqual(text, caption)
                self.assertEqual(changes, [])


if __name__ == '__main__':
    unittest.main()
