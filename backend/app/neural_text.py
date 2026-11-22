"""Punctuation-only preparation for model input; source transcripts stay intact."""
INPUT_NORMALIZATION='terminal-punctuation-v2'

def model_caption(text):
    caption=text.strip()
    # ASR chunks may end on a comma/colon. Appending a period to them creates
    # compact-vocabulary tokens such as ',.' that are absent from the model.
    if caption.endswith((',', ';', ':')):
        caption=caption.rstrip(',;:').rstrip()
    if caption and not caption.endswith(('.', '!', '?')):caption+='.'
    return caption
