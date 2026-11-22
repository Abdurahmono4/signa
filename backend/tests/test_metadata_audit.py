from scripts.audit_how2sign_metadata import read_rows,compare

def test_realigned_requires_context_outside_original_clip(tmp_path):
    original=tmp_path/'original.csv';realigned=tmp_path/'realigned.csv'
    original.write_text('SENTENCE_NAME\tVIDEO_NAME\tSENTENCE\tSTART\tEND\na\tv\tHello\t10\t12\nb\tv\tBye\t12\t14\n')
    realigned.write_text('SENTENCE_NAME\tVIDEO_NAME\tSENTENCE\tSTART_REALIGNED\tEND_REALIGNED\na\tv\tHello\t9\t13\nb\tv\tBye\t12.5\t13.5\n')
    a,issues,_=read_rows(original);b,other,_=read_rows(realigned,True)
    assert not issues and not other
    result=compare(a,b)
    assert result['timing_changed']==2 and result['realigned_interval_extends_outside_original_clip']==1

def test_invalid_intervals_and_duplicate_ids_are_reported(tmp_path):
    p=tmp_path/'bad.csv';p.write_text('SENTENCE_NAME\tVIDEO_NAME\tSENTENCE\tSTART\tEND\na\tv\tHi\t0\t1\na\tv\tHi\t0\t1\nb\tv\tBye\tnan\t2\nc\tv\tBye\t4\t2\n')
    rows,issues,count=read_rows(p)
    assert count==4 and len(rows)==1 and len(issues)==3
