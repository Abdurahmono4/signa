"""Score a local job against an independently prepared reference TXT."""
import argparse,json,sys,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.app.core import get_job
from backend.app.asr_metrics import word_errors

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--job',required=True);p.add_argument('--reference',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Output exists; choose a new report filename')
    job=get_job(a.job)
    if not job or not job.get('segments'):raise ValueError('Job transcript missing')
    if job['status'] in ['queued','processing']:raise ValueError('Wait for transcription completion')
    reference=a.reference.read_text(encoding='utf-8-sig');hypothesis=' '.join(s['text'] for s in job['segments'])
    report={'job_id':a.job,'reference_file':str(a.reference.resolve()),'reference_sha256':hashlib.sha256(reference.encode()).hexdigest(),
            'hypothesis':hypothesis,'transcript_revision':job.get('transcript_revision',0),'edited_transcript':bool(job.get('transcript_revision',0)),**word_errors(reference,hypothesis)}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report))
