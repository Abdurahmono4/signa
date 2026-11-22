import pytest
from backend.app.neural_text import model_caption
from backend.app.neural_preflight import check_segments

@pytest.mark.parametrize('source,expected',[
 ('In order to obtain that,','In order to obtain that.'),
 ('A sentence;','A sentence.'),('An introduction:','An introduction.'),
 ('Hello, friend!','Hello, friend!'),('  Mr. Smith arrived.  ','Mr. Smith arrived.'),
 ('Hello there','Hello there.'),('Why?','Why?'),('','')])
def test_model_punctuation_preserves_words_and_internal_punctuation(source,expected):
    assert model_caption(source)==expected

def test_trailing_comma_never_becomes_unsupported_comma_dot_token():
    segments=[{'id':'0','text':'In order to obtain that,','start':1,'end':3}]
    result=check_segments(segments,lambda text:text.split(),{'In','order','to','obtain','that.'})
    assert result['compatible'] and not result['unsupported_chunks']
    assert segments[0]['text']=='In order to obtain that,'
