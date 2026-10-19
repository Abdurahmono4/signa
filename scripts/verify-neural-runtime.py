"""Write a runtime readiness marker only after actual CPU model imports pass."""
import argparse
import datetime
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model-root',type=Path,default=Path(__file__).resolve().parents[1]/'backend/models/MaDiS')
    args=parser.parse_args()
    root=args.model_root.resolve();runtime=root/'runtime';source=root/'source'
    manifest=json.loads(Path(__file__).with_name('neural-model-manifest.json').read_text(encoding='utf-8'))
    commit=subprocess.run(['git','-C',str(source),'rev-parse','HEAD'],capture_output=True,text=True,check=True).stdout.strip()
    if commit!=manifest['source_commit']:
        raise RuntimeError('The official source revision differs from the pinned release')
    dirty=subprocess.run(['git','-C',str(source),'status','--porcelain'],capture_output=True,text=True,check=True).stdout
    if dirty.strip():
        raise RuntimeError('Official MaDiS source has local changes; preserve them and use an unmodified source checkout')
    sys.path.insert(0,str(source))
    import torch,numpy,transformers,accelerate
    from transformers import Qwen3Config,Qwen3ForCausalLM
    from mGPT.archs.madis import MaDiSLanguageModel
    from mGPT.archs.mgpt_vq import VQVae
    if (torch.__version__!='2.5.0+cpu' or transformers.__version__!='4.51.0'
            or numpy.__version__!='1.26.4' or torch.version.cuda is not None):
        raise RuntimeError('The isolated CPU runtime versions differ from the tested versions')
    config=Qwen3Config(vocab_size=64,hidden_size=32,intermediate_size=64,num_hidden_layers=1,
                       num_attention_heads=4,num_key_value_heads=2,head_dim=8,use_sliding_window=False)
    model=Qwen3ForCausalLM(config).eval()
    with torch.inference_mode():
        logits=model(torch.tensor([[1,2,3]])).logits
    if tuple(logits.shape)!=(1,3,64) or not logits.isfinite().all():
        raise RuntimeError('CPU language-model smoke check failed')
    runtime.mkdir(parents=True,exist_ok=True)
    # The generation path uses from_pretrained/device_map. It needs Accelerate
    # even when a direct Qwen3(config) constructor already works.
    with tempfile.TemporaryDirectory(prefix='.signa-verify-',dir=runtime) as temporary:
        model.save_pretrained(temporary,safe_serialization=True)
        loaded=Qwen3ForCausalLM.from_pretrained(temporary,device_map='cpu',local_files_only=True)
        with torch.inference_mode():
            restored=loaded(torch.tensor([[1,2,3]])).logits
        if not torch.allclose(logits,restored,atol=1e-6):
            raise RuntimeError('CPU from_pretrained/device_map verification failed')
    marker={'ready':True,'python':sys.version.split()[0],'device':'cpu','source_commit':commit,
            'versions':{name:importlib.metadata.version(name) for name in
                ['torch','transformers','numpy','accelerate','omegaconf','safetensors','sentencepiece','einops','tokenizers','huggingface-hub']},
            'verified_imports':['torch','transformers.Qwen3Config','transformers.Qwen3ForCausalLM',
                'mGPT.archs.madis.MaDiSLanguageModel','mGPT.archs.mgpt_vq.VQVae'],
            'verified_cpu_forward':'Qwen3 tiny config and from_pretrained/device_map CPU finite matching logits1x3x64',
            'verified_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    runtime.mkdir(parents=True,exist_ok=True)
    temp=runtime/'.signa-ready.tmp'
    temp.write_text(json.dumps(marker,indent=2),encoding='utf-8')
    temp.replace(runtime/'.signa-ready.json')
    freeze=subprocess.run([sys.executable,'-m','pip','freeze'],capture_output=True,text=True,check=True).stdout
    (runtime/'requirements-installed.txt').write_text(freeze,encoding='utf-8')
    print(json.dumps(marker,indent=2))


if __name__=='__main__':
    main()
