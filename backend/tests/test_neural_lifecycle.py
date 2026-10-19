"""Queue/API control tests use tiny child-process fixtures, never model outputs."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from unittest.mock import Mock

import test_api
from app import main,neural


class NeuralLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory()
        self.root=Path(self.temporary.name)
        self.data=self.root/'data';self.data.mkdir()
        self.patches=[patch.object(neural,name,{}) for name in ['_states','_cancel','_processes']]
        for item in self.patches:item.start()
        self.children=[];self.threads=[]
        self.real_popen=subprocess.Popen
        def stop_fixture(child):
            if child.poll() is None:child.terminate()
            child.wait(timeout=5)
        # The fixture uses the base interpreter, with no Windows venv child.
        # Process-tree policy is tested separately against the real helper.
        self.stop_patch=patch.object(neural,'stop_process',side_effect=stop_fixture)
        self.stop_mock=self.stop_patch.start()

    def tearDown(self):
        neural.shutdown()
        for child in self.children:
            if child.poll() is None:
                child.kill()
            child.wait(timeout=5)
        for thread in self.threads:thread.join(timeout=5)
        for child in self.children:
            if child.stdout:child.stdout.close()
        self.stop_patch.stop()
        for item in reversed(self.patches):item.stop()
        self.temporary.cleanup()

    def row(self):
        return {'id':'fixture','revision':1,'duration':10.,'segments':json.dumps([
            {'start':1.,'end':3.,'text':'First sentence.'},
            {'start':5.,'end':7.,'text':'Second sentence.'}])}

    def factory(self,script,launched=None):
        def launch(command,**options):
            # Exercise real pipes, process polling and termination, replacing
            # only the expensive external neural program with a tiny fixture.
            child=self.real_popen([sys._base_executable,'-u','-c',script],**options)
            self.children.append(child)
            if launched:launched.set()
            return child
        return launch

    def prime(self,row,stop):
        key=neural.key_for(row)
        neural._states[key]={'status':'queued','phase':'queued','progress':0,'key':key}
        neural._cancel[key]=stop
        return key

    def test_cancel_terminates_real_child_releases_lock_and_does_not_publish_plan(self):
        row=self.row();launched=threading.Event();lock=threading.Lock()
        with patch.object(neural.subprocess,'Popen',side_effect=self.factory('import time;time.sleep(60)',launched)):
            neural.enqueue(self.root,self.data,row,lock,lambda:None)
            self.assertTrue(launched.wait(5),'Fixture child must launch')
            key=neural.key_for(row)
            self.assertEqual(neural.enqueue(self.root,self.data,row,lock,lambda:None)['key'],key)
            self.assertEqual(len(self.children),1,'Duplicate submission must reuse the running job')
            with self.assertRaises(RuntimeError):
                neural.enqueue(self.root,self.data,{**row,'id':'another'},lock,lambda:None)
            self.assertTrue(neural.cancel(row))
            self.children[0].wait(timeout=5)
            # The process has stopped, but the worker needs to publish its state.
            finished=threading.Event()
            def watch():
                for _ in range(100):
                    if (neural.status(self.data,row)['status']=='cancelled'
                            and key not in neural._processes and key not in neural._cancel):finished.set();return
                    finished.wait(.02)
            watcher=threading.Thread(target=watch);watcher.start();watcher.join(3)
            self.assertTrue(finished.is_set())
        self.assertFalse((neural.folder(self.data,row)/'plan.json').exists())
        self.assertIsNotNone(self.children[0].poll())
        self.assertTrue(lock.acquire(blocking=False));lock.release()
        self.assertNotIn(key,neural._processes)
        self.assertNotIn(key,neural._cancel)
        self.stop_mock.assert_any_call(self.children[0])

    def test_timeout_stops_child_and_keeps_partial_output_unpublished(self):
        row=self.row();stop=threading.Event();key=self.prime(row,stop)
        with (patch.object(neural.subprocess,'Popen',side_effect=self.factory('import time;time.sleep(60)')),
                patch.object(neural.time,'monotonic',side_effect=[0.,2001.])):
            neural._generate(self.root,self.data,row,threading.Lock(),lambda:None,stop)
        self.assertEqual(neural._states[key]['status'],'failed')
        self.assertIn('vaqti tugadi',neural._states[key]['error'])
        self.assertIsNotNone(self.children[0].poll(),'A timed-out model child must be reaped')
        self.assertFalse((neural.folder(self.data,row)/'plan.json').exists())
        self.assertNotIn(key,neural._processes)

    def test_partial_or_empty_model_index_never_publishes_empty_translation(self):
        cases=[('ready',[]),('ready',[{'id':'0','duration':1.}]),
               ('processing',[{'id':'0','duration':1.},{'id':'1','duration':1.}])]
        for status,motions in cases:
            with self.subTest(status=status,motions=motions):
                row={**self.row(),'id':f'fixture-{len(motions)}'}
                stop=threading.Event();key=self.prime(row,stop)
                out=neural.folder(self.data,row)/'motion'
                script=('from pathlib import Path;import json;'
                        f'p=Path({str(out)!r});p.mkdir(parents=True,exist_ok=True);'
                        f'(p/"index.json").write_text({json.dumps({"status":status,"motions":motions})!r})')
                with patch.object(neural.subprocess,'Popen',side_effect=self.factory(script)):
                    neural._generate(self.root,self.data,row,threading.Lock(),lambda:None,stop)
                self.assertEqual(neural._states[key]['status'],'failed')
                self.assertFalse((neural.folder(self.data,row)/'plan.json').exists())
                self.assertNotEqual(neural.status(self.data,row)['status'],'ready')

    def test_already_cancelled_queue_does_not_load_or_launch_model(self):
        row=self.row();stop=threading.Event();stop.set();key=self.prime(row,stop)
        with patch.object(neural.subprocess,'Popen') as launch,patch.object(main,'release_speech_model') as release:
            neural._generate(self.root,self.data,row,threading.Lock(),release,stop)
        launch.assert_not_called();release.assert_not_called()
        self.assertEqual(neural._states[key]['status'],'cancelled')
        self.assertFalse((neural.folder(self.data,row)/'plan.json').exists())


class NeuralArtifactApiTests(unittest.TestCase):
    setUp=test_api.APITest.setUp
    tearDown=test_api.APITest.tearDown

    def ready_job(self):
        uploaded=self.client.post('/api/jobs',files={'file':('fixture.wav',test_api.wav_bytes(),'audio/wav')}).json()
        self.client.put(f"/api/jobs/{uploaded['id']}/transcript",json={'revision':0,'segments':[
            {'start':0,'end':.9,'text':'Fixture sentence.'}]})
        return main.get_row(uploaded['id'])

    def test_revision_change_rejects_old_motion_key_and_does_not_reuse_old_plan(self):
        row=self.ready_job();base=neural.folder(main.DATA,row);motion=base/'motion';motion.mkdir(parents=True)
        # Artifact/control fixtures are deliberately not valid generated ASL.
        (base/'plan.json').write_text(json.dumps({'fixture':'cached plan metadata'}),encoding='utf-8')
        (motion/'0.json').write_text(json.dumps({'fixture':'motion metadata'}),encoding='utf-8')
        (motion/'index.json').write_text(json.dumps({'motions':[{'id':'0','motion_json':'0.json'}]}),encoding='utf-8')
        key=neural.key_for(row);url=f"/api/jobs/{row['id']}/neural"
        self.assertEqual(self.client.get(url+'/plan').status_code,200)
        self.assertEqual(self.client.get(url+f'/motions/0?key={key}').status_code,200)
        self.client.put(f"/api/jobs/{row['id']}/transcript",json={'revision':row['revision'],'segments':[
            {'start':0,'end':.9,'text':'Changed fixture sentence.'}]})
        self.assertEqual(self.client.get(url+f'/motions/0?key={key}').status_code,409)
        self.assertEqual(self.client.get(url+'/plan').status_code,409)
        current=self.client.get(url).json()
        self.assertEqual(current['status'],'idle');self.assertNotEqual(current['key'],key)
        self.assertTrue((base/'plan.json').is_file(),'Old history is preserved, but cannot masquerade as current output')

    def test_motion_index_cannot_escape_its_cache_directory(self):
        row=self.ready_job();base=neural.folder(main.DATA,row)/'motion';base.mkdir(parents=True)
        outside=Path(self.tmp.name)/'outside.json';outside.write_text('private fixture',encoding='utf-8')
        key=neural.key_for(row);url=f"/api/jobs/{row['id']}/neural/motions"
        for path in ['../../../../outside.json',str(outside.resolve())]:
            with self.subTest(path=path):
                (base/'index.json').write_text(json.dumps({'motions':[{'id':'0','motion_json':path}]}),encoding='utf-8')
                response=self.client.get(url+f'/0?key={key}')
                self.assertEqual(response.status_code,404)
                self.assertNotIn('private fixture',response.text)
        self.assertEqual(self.client.get(url+f'/not-a-number?key={key}').status_code,422)
        self.assertEqual(self.client.get(url+f'/999?key={key}').status_code,404)
        self.assertEqual(outside.read_text(encoding='utf-8'),'private fixture')


class NeuralProcessTreeTests(unittest.TestCase):
    def test_windows_cancel_targets_only_owned_process_tree_and_reaps_parent(self):
        process=Mock(pid=4321);process.poll.return_value=None
        with (patch.object(neural,'os',SimpleNamespace(name='nt')),
              patch.object(neural.subprocess,'run') as kill_tree):
            kill_tree.return_value=SimpleNamespace(returncode=0)
            neural.stop_process(process)
        self.assertEqual(kill_tree.call_args.args[0],['taskkill','/PID','4321','/T','/F'])
        self.assertEqual(kill_tree.call_args.kwargs['timeout'],15)
        process.wait.assert_called_once_with(timeout=10)
        process.terminate.assert_not_called()

    def test_stop_wait_timeout_uses_kill_then_reaps(self):
        process=Mock(pid=4321);process.poll.return_value=None
        process.wait.side_effect=[subprocess.TimeoutExpired('fixture',10),0]
        with patch.object(neural,'os',SimpleNamespace(name='posix')):
            neural.stop_process(process)
        process.terminate.assert_called_once();process.kill.assert_called_once()
        self.assertEqual(process.wait.call_count,2)

    def test_finished_process_is_never_signalled_again(self):
        process=Mock(pid=4321);process.poll.return_value=0
        with patch.object(neural.subprocess,'run') as kill_tree:
            neural.stop_process(process)
        kill_tree.assert_not_called();process.terminate.assert_not_called();process.kill.assert_not_called()

    def test_windows_tree_stop_failure_falls_back_and_still_reaps(self):
        for failure in [OSError('fixture missing utility'),subprocess.TimeoutExpired('taskkill',15)]:
            with self.subTest(error=type(failure).__name__):
                process=Mock(pid=4321);process.poll.return_value=None
                with (patch.object(neural,'os',SimpleNamespace(name='nt')),
                      patch.object(neural.subprocess,'run',side_effect=failure)):
                    neural.stop_process(process)
                process.terminate.assert_called_once();process.wait.assert_called_once_with(timeout=10)
