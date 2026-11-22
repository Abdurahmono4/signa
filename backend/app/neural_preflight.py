"""Token compatibility check without loading the neural motion model."""
import io,pickle
from functools import lru_cache
from pathlib import Path
from tokenizers import Tokenizer,AddedToken
from .neural_text import model_caption

class DataOnly(pickle.Unpickler):
    def find_class(self,*args):raise ValueError('Only plain mapping data is allowed')
    def persistent_load(self,*args):raise ValueError('Persistent objects are not allowed')

@lru_cache(maxsize=2)
def load(token_path,map_path,token_size,token_mtime,map_size,map_mtime):
    if token_size>16*1024*1024 or map_size>2*1024*1024:raise ValueError('Tokenizer metadata exceeds limit')
    mapping=DataOnly(io.BytesIO(Path(map_path).read_bytes())).load()
    if not isinstance(mapping,dict) or len(mapping)>200000 or not all(type(k)is int and type(v)is int for k,v in mapping.items()):raise ValueError('Invalid compact mapping')
    tokenizer=Tokenizer.from_file(token_path)
    tokens=[f'<{part}_id_{n}>' for part,size in [('motion',96),('hand',192),('rhand',192)] for n in range(size+3)]
    tokenizer.add_special_tokens([AddedToken('<mask>',special=True)])
    tokenizer.add_tokens(tokens)
    supported=set(mapping);supported.update(tokenizer.token_to_id(t) for t in ['<mask>',*tokens])
    return tokenizer,frozenset(supported)

def check_segments(segments,tokenize,supported):
    unsupported=[]
    for i,segment in enumerate(segments):
        text=model_caption(segment['text'])
        if all(token in supported for token in tokenize(text)):continue
        if all(token in supported for token in tokenize(text.lower())):continue
        unsupported.append({'segment_index':segment.get('segment_index',i),'chunk_id':segment.get('id',str(i)),'start':segment.get('start'),'end':segment.get('end')})
    return {'compatible':not unsupported,'checked_chunks':len(segments),'unsupported_chunks':unsupported,'scope':'Tokenizer compatibility only; not sign-language accuracy'}

def inspect(root,segments):
    base=Path(root)/'models/MaDiS/assets/Qwen3-0.6B-Base-en-zh-de'
    token=base/'tokenizer.json';mapping=base/'map_ids.pkl';t,m=token.stat(),mapping.stat()
    tokenizer,supported=load(str(token),str(mapping),t.st_size,t.st_mtime_ns,m.st_size,m.st_mtime_ns)
    return check_segments(segments,lambda text:tokenizer.encode(text,add_special_tokens=True).ids,supported)
