"""Isolate all tests before any app module is imported during collection."""
import os,tempfile,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
test_root=Path(tempfile.mkdtemp(prefix='signbridge-pytest-'))
os.environ['SIGNBRIDGE_STORAGE']=str(test_root/'storage')
os.environ['SIGNBRIDGE_ASSETS']=str(test_root/'assets')
os.environ['SIGNBRIDGE_DATASET']=str(test_root/'dataset')
for path in ['storage','assets/animations','assets/avatars','dataset']:(test_root/path).mkdir(parents=True,exist_ok=True)
