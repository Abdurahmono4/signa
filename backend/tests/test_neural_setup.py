import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

SCRIPTS=Path(__file__).resolve().parents[2]/'scripts'
spec=importlib.util.spec_from_file_location('download_neural_model',SCRIPTS/'download-neural-model.py')
setup=importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


class NeuralSetupTests(unittest.TestCase):
    def test_required_assets_are_pinned_hashed_and_exclude_unused_or_mesh_models(self):
        manifest=json.loads((SCRIPTS/'neural-model-manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['source_commit'],'071828ea1b94530dc7ff0a6c009c0a7c6d1f0784')
        self.assertEqual(manifest['revision'],'ceaed59c964820f2c13401a0870b2988686956ad')
        self.assertEqual({item['path'] for item in manifest['files']},
                         {'sft_how2sign.ckpt','Qwen3-0.6B-Base-en-zh-de.zip','mean.pt','std.pt'})
        self.assertEqual(sum(item['size'] for item in manifest['files']),7198549119)
        for item in manifest['files']+[manifest['torch']]:
            self.assertRegex(item['sha256'],r'^[0-9a-f]{64}$')
            self.assertGreater(item['size'],0)

    def test_verifier_rejects_same_size_corrupted_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'fixture'
            record={'size':4,'sha256':hashlib.sha256(b'good').hexdigest()}
            path.write_bytes(b'good');self.assertTrue(setup.verified(path,record))
            path.write_bytes(b'evil');self.assertFalse(setup.verified(path,record))
            path.write_bytes(b'goodx');self.assertFalse(setup.verified(path,record))

    def test_language_archive_extracts_required_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);archive=root/'qwen.zip';destination=root/'assets';destination.mkdir()
            with zipfile.ZipFile(archive,'w') as handle:
                handle.writestr('Qwen3-0.6B-Base-en-zh-de/config.json','{}')
                handle.writestr('Qwen3-0.6B-Base-en-zh-de/map_ids.pkl',b'fixture, never unpickled')
            setup.extract_qwen(archive,destination)
            self.assertTrue((destination/'Qwen3-0.6B-Base-en-zh-de/config.json').is_file())

    def test_archive_traversal_is_rejected_before_any_file_is_written(self):
        for unsafe in ['../escape','..\\escape','/absolute','C:/outside']:
            with self.subTest(path=unsafe),tempfile.TemporaryDirectory() as temporary:
                root=Path(temporary);archive=root/'qwen.zip';destination=root/'assets';destination.mkdir()
                with zipfile.ZipFile(archive,'w') as handle:
                    handle.writestr('safe.txt','must not be extracted before validation')
                    handle.writestr(unsafe,'bad')
                with self.assertRaises(ValueError):
                    setup.extract_qwen(archive,destination)
                self.assertEqual(list(destination.iterdir()),[])


if __name__=='__main__':
    unittest.main()
