import uuid
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core import STORE,save_job,get_job

def test_exact_export_links_survive_new_render_and_cancel():
    with TestClient(app) as client:
        id=uuid.uuid4().hex;token=uuid.uuid4().hex;folder=STORE/id/token;folder.mkdir(parents=True)
        (folder/'result.mp4').write_bytes(b'previous complete video fixture')
        save_job({'id':id,'status':'done','duration':1,'segments':[],'translation':{'items':[]},'result_token':token,'settings':{'engine':'human'}})
        r=client.post(f'/api/jobs/{id}/render/start',json={});assert r.status_code==200
        session=r.json();assert get_job(id)['previous_results'][0]['token']==token
        for endpoint in ['result','download']:
            r=client.get(f'/api/jobs/{id}/{endpoint}?v={token}')
            assert r.status_code==200 and r.content==b'previous complete video fixture'
            assert r.headers['x-export-version']==token and r.headers['cache-control']=='no-store'
        assert client.get(f'/api/jobs/{id}/result').status_code==409
        partial=STORE/id/session['token']/'result.mp4';partial.write_bytes(b'partial should not be downloadable')
        assert client.get(f"/api/jobs/{id}/result?v={session['token']}").status_code==404
        assert client.post(f'/api/jobs/{id}/cancel').status_code==200
        assert client.get(f'/api/jobs/{id}/download?v={token}').status_code==200
        newer=uuid.uuid4().hex;(STORE/id/newer).mkdir();(STORE/id/newer/'result.mp4').write_bytes(b'new complete video fixture')
        job=get_job(id);job.update(status='done',result_token=newer);save_job(job)
        assert client.get(f'/api/jobs/{id}/result').content==b'new complete video fixture'
        assert client.get(f'/api/jobs/{id}/result?v={token}').content==b'previous complete video fixture'
        assert client.get(f'/api/jobs/{id}/result?v={uuid.uuid4().hex}').status_code==404
        assert client.get(f'/api/jobs/{id}/result?v=../../private').status_code==404
        (STORE/id/newer/'result.mp4').unlink()
        assert client.get(f'/api/jobs/{id}/result').status_code==404
