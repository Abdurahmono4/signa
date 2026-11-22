import pytest
from backend.app.asr_metrics import word_errors

def test_missing_words_and_substitutions_and_insertions():
    assert word_errors('one two three','one three')['deletions']==1
    assert word_errors('one two three','one too three')['substitutions']==1
    assert word_errors('one two','one two three')['insertions']==1
    assert word_errors('Hello, WORLD!','hello world')['wer_percent']==0
    r=word_errors('one','one two three');assert r['wer_percent']==200
    assert word_errors('one two','')['deletions']==2
    with pytest.raises(ValueError):word_errors('','hello')
