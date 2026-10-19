"""Isolated CPU adapter for the official MaDiS How2Sign checkpoint.

Run with backend/models/MaDiS/runtime/.venv/Scripts/python.exe. The main API
environment does not need torch. Upstream remains unmodified and is excluded
from the distributable source archive. This runner does not load SMPL-X meshes,
training datasets, metrics, or any human-model registration assets.
"""
from __future__ import annotations

import argparse
import collections
import codecs
import enum
import gc
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import typing


SOURCE_COMMIT = '071828ea1b94530dc7ff0a6c009c0a7c6d1f0784'
HF_REVISION = 'ceaed59c964820f2c13401a0870b2988686956ad'
CHECKPOINT_SHA256 = 'd3953f89a74a2b2a8bbce6a9dd9aba4751c81c03e2d8fe8511f0ae7ce2727302'
CHECKPOINT_BYTES = 6295891758
FEATURE_FORMAT = 'signa-madis-133-v1'
DECODER_GUARD = 'nonempty-motion-token-v2'
INPUT_NORMALIZATION = 'terminal-punctuation-compact-vocabulary-v1'
FEATURE_LAYOUT = {
    'representation': 'axis_angle_radians',
    'upper_body': {'slice': [0, 30], 'joint_names': [
        'neck', 'left_collar', 'right_collar', 'head', 'left_shoulder',
        'right_shoulder', 'left_elbow', 'right_elbow', 'left_wrist', 'right_wrist']},
    'left_hand': {'slice': [30, 75], 'joint_names': [
        f'{finger}_{joint}' for finger in ('index', 'middle', 'pinky', 'ring', 'thumb')
        for joint in (1, 2, 3)]},
    'right_hand': {'slice': [75, 120], 'same_order_as': 'left_hand'},
    'jaw': {'slice': [120, 123]},
    'expression': {'slice': [123, 133], 'representation': 'SMPL-X_expression_coefficients'},
    'root_and_lower_body': 'Not generated; freeze target avatar neutral lower body.',
}


def event(event_name: str, **values):
    print(json.dumps({'event': event_name, **values}, ensure_ascii=False), flush=True)


def _check_source(source: Path):
    expected = source / 'mGPT' / 'archs' / 'madis.py'
    if not expected.is_file():
        raise FileNotFoundError(f'Official MaDiS source is missing: {source}')
    result = subprocess.run(['git', '-C', str(source), 'rev-parse', 'HEAD'],
                            capture_output=True, text=True, check=True)
    if result.stdout.strip() != SOURCE_COMMIT:
        raise RuntimeError('MaDiS source revision differs from the audited release.')


def _verify_checkpoint(path: Path):
    if not path.is_file() or path.stat().st_size != CHECKPOINT_BYTES:
        raise FileNotFoundError('The complete official ASL checkpoint is not available yet.')
    # Cache is tied to exact file metadata; a partial/replaced download is checked again.
    stat = path.stat()
    cache = path.with_name(path.name + '.signa-verified.json')
    fingerprint = {'bytes': stat.st_size, 'mtime_ns': stat.st_mtime_ns,
                   'expected_sha256': CHECKPOINT_SHA256}
    try:
        if json.loads(cache.read_text(encoding='utf-8')) == fingerprint:
            return
    except (OSError, ValueError):
        pass
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b''):
            digest.update(block)
    if digest.hexdigest() != CHECKPOINT_SHA256:
        raise RuntimeError('ASL model checkpoint SHA-256 verification failed.')
    cache.write_text(json.dumps(fingerprint), encoding='utf-8')


def _safe_metadata_globals(np):
    """Explicit passive metadata types; never retry unrestricted pickle loading."""
    from omegaconf import DictConfig, ListConfig
    from omegaconf.base import ContainerMetadata, Metadata
    from omegaconf.nodes import AnyNode
    allowed = [DictConfig, ListConfig, ContainerMetadata, Metadata, AnyNode,
               collections.OrderedDict, collections.defaultdict, typing.Any,
               list, dict, set, tuple, int, float, str, bytes, enum.Enum,
               np.ndarray, np.dtype, np.core.multiarray._reconstruct,
               codecs.encode,
               type(np.dtype(np.float32)), type(np.dtype(np.float64)),
               type(np.dtype(np.int64))]
    # Released training metadata was saved with NumPy 2; the isolated runtime
    # uses NumPy 1.26. This explicitly named passive ndarray reconstruction is
    # the same operation, without importing or executing a foreign module.
    def numpy2_reconstruct(*args):
        return np.core.multiarray._reconstruct(*args)
    numpy2_reconstruct.__module__ = 'numpy._core.multiarray'
    numpy2_reconstruct.__name__ = '_reconstruct'
    allowed.append(numpy2_reconstruct)
    for module, name in [
        ('mGPT.data.humanml.utils.word_vectorizer', 'WordVectorizer'),
        ('mGPT.utils.load_checkpoint', '_LegacyWordVectorizer'),
    ]:
        # The checkpoint's legacy word-vector metadata is unused. A passive
        # placeholder avoids importing the original training data loader.
        allowed.append(type(name, (), {'__module__': module}))
    return allowed


def _load_state(path, torch, np):
    with torch.serialization.safe_globals(_safe_metadata_globals(np)):
        checkpoint = torch.load(path, map_location='cpu', mmap=True, weights_only=True)
    if not isinstance(checkpoint, dict) or 'state_dict' not in checkpoint:
        raise ValueError('Expected an official Lightning checkpoint with state_dict.')
    state = checkpoint['state_dict']
    if not isinstance(state, (dict, collections.OrderedDict)):
        raise ValueError('Model state_dict is not a tensor mapping.')
    if any(not isinstance(value, torch.Tensor) for value in state.values()):
        raise ValueError('Non-tensor model state entries are not supported.')
    return state


def _component_state(state, prefix):
    result = {key[len(prefix):]: value for key, value in state.items() if key.startswith(prefix)}
    if not result:
        raise ValueError(f'Checkpoint lacks required component {prefix}')
    return result


def _load_stats(path, torch):
    stats = torch.load(path, map_location='cpu', weights_only=True).float().flatten()
    if stats.numel() != 179:
        raise ValueError(f'Unexpected normalization dimensions in {path.name}: {stats.numel()}')
    stats = stats[36:]
    return torch.cat((stats[:-20], stats[-10:]))


def require_motion_tokens(raw_streams, valid_ids):
    """Reject an empty model result before upstream substitutes code zero.

    This check uses embedding IDs for actual codebook entries, excluding all
    text, PAD/EOS, mask, and the three non-codebook part tokens. It deliberately
    makes no claim about the meaning or completeness of a nonempty sequence.
    Kept independent of torch so the boundary can be tested without weights.
    """
    counts = {}
    for part in ('body', 'left_hand', 'right_hand'):
        allowed = set(valid_ids.get(part, ()))
        counts[part] = sum(token in allowed for token in raw_streams.get(part, ()))
        if not counts[part]:
            raise ValueError(
                f'ASL modeli haqiqiy ishora tokenlarini yaratmadi ({part}). '
                'Qisqaroq, tugallangan inglizcha gap bilan qayta urinib ko‘ring.')
    return counts


def prepare_model_input(text, tokenize, compact_vocabulary):
    """Keep words intact and never silently map unsupported text to PAD/EOS."""
    caption = text.strip()
    normalizations = []
    if caption and not caption.endswith(('.', '!', '?')):
        caption += '.'
        normalizations.append('terminal_punctuation')
    if all(token in compact_vocabulary for token in tokenize(caption)):
        return caption, normalizations
    lower = caption.lower()
    if all(token in compact_vocabulary for token in tokenize(lower)):
        return lower, normalizations + ['lowercase_for_compact_vocabulary']
    raise ValueError(
        'Unsupported text tokens: ASL modelining qisqartirilgan lug‘ati bu '
        'matnni to‘liq qabul qila olmadi. Inglizcha matnni tekshiring.')


def _qwen_directory(root: Path):
    candidates = [root / 'assets' / 'Qwen3-0.6B-Base-en-zh-de',
                  root / 'source' / 'deps' / 'Qwen3-0.6B-Base-en-zh-de']
    for candidate in candidates:
        if (candidate / 'config.json').is_file() and (candidate / 'map_ids.pkl').is_file():
            return candidate
    raise FileNotFoundError('Extract the official Qwen3-0.6B-Base-en-zh-de.zip into assets/.')


def run(request: dict, output: Path, root: Path):
    batched = 'segments' in request
    segments = request.get('segments') if batched else [{'id': '0', 'text': request.get('text')}]
    if not isinstance(segments, list) or not 1 <= len(segments) <= 512:
        raise ValueError('Provide 1–512 text segments.')
    ids = set()
    for index, segment in enumerate(segments):
        if not isinstance(segment, dict) or not isinstance(segment.get('text'), str):
            raise ValueError('Each segment must be an object containing English text.')
        segment['text'] = segment['text'].strip()
        if not segment['text'] or len(segment['text']) > 1500 or len(segment['text'].split()) > 40:
            raise ValueError('Each English segment must contain 1–40 words and at most 1500 characters; split longer text before inference.')
        segment['id'] = str(segment.get('id', index))
        if not segment['id'] or len(segment['id']) > 150 or segment['id'] in ids:
            raise ValueError('Segment IDs must be unique nonempty strings of at most 150 characters.')
        ids.add(segment['id'])
    max_tokens = int(request.get('max_tokens', 100))
    if not 4 <= max_tokens <= 100:
        raise ValueError('max_tokens must be between 4 and 100.')
    threads = int(request.get('threads', min(8, os.cpu_count() or 1)))
    if not 1 <= threads <= 16:
        raise ValueError('threads must be between 1 and 16.')
    seed = int(request.get('seed', 1234))
    source, assets = root / 'source', root / 'assets'
    _check_source(source)
    qwen = _qwen_directory(root)
    checkpoint = assets / 'sft_how2sign.ckpt'
    event('progress', stage='verifying_model', message='ASL model is being verified.')
    _verify_checkpoint(checkpoint)
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    os.environ['TOKENIZERS_PARALLELISM'] = 'false'
    sys.path.insert(0, str(source))
    import numpy as np
    import torch
    import torch.nn.functional as F
    from mGPT.archs.mgpt_vq import VQVae
    from mGPT.archs.madis import MaDiSLanguageModel

    torch.set_num_threads(threads)
    torch.set_num_interop_threads(min(2, threads))
    torch.manual_seed(seed)
    np.random.seed(seed % (2**32))
    started = time.perf_counter()
    event('progress', stage='loading_model', message='The neural ASL model is loading on CPU.')
    state = _load_state(checkpoint, torch, np)
    params = dict(code_dim=512, output_emb_width=512, down_t=2, stride_t=2,
                  width=512, depth=3, dilation_growth_rate=3, norm=None, activation='relu')
    body = VQVae(nfeats=43, code_num=96, **params)
    left = VQVae(nfeats=45, code_num=192, **params)
    right = VQVae(nfeats=45, code_num=192, **params)
    for component, prefix in [(body, 'vae.'), (left, 'hand_vae.'), (right, 'rhand_vae.')]:
        component.load_state_dict(_component_state(state, prefix), strict=True)
        component.eval().requires_grad_(False)
    lm = MaDiSLanguageModel(
        model_path=str(qwen), stage='lm_instruct', motion_codebook_size=96,
        hand_codebook_size=192, rhand_codebook_size=192,
        body_codebook=body.quantizer.codebook.detach().clone(),
        hand_codebook=left.quantizer.codebook.detach().clone(),
        rhand_codebook=right.quantizer.codebook.detach().clone(),
    )
    lm.load_state_dict(_component_state(state, 'lm.'), strict=True)
    lm.eval().requires_grad_(False)
    stream_specs = [
        ('body', 'outputs_re', 'motion', 96),
        ('left_hand', 'outputs_hand', 'hand', 192),
        ('right_hand', 'outputs_rhand', 'rhand', 192),
    ]
    valid_ids = {
        part: {lm.tok_id_to_emb_id[lm.tokenizer.convert_tokens_to_ids(
            f'<{prefix}_id_{code}>')] for code in range(limit)}
        for part, _, prefix, limit in stream_specs
    }
    del state
    gc.collect()
    mean, std = _load_stats(assets / 'mean.pt', torch), _load_stats(assets / 'std.pt', torch)
    if not torch.isfinite(mean).all() or not torch.isfinite(std).all():
        raise ValueError('Normalization values must be finite.')
    load_seconds = time.perf_counter() - started
    event('progress', stage='generating_motion', message='English text is being converted to continuous ASL motion.',
          model_load_seconds=round(load_seconds, 3))
    output.mkdir(parents=True, exist_ok=True)
    results = []
    for index, segment in enumerate(segments):
        event('progress', stage='generating_segment', segment_id=segment['id'], segment_index=index,
              segment_count=len(segments), completed_segments=len(results))
        generated_at = time.perf_counter()
        model_input_text, input_normalizations = prepare_model_input(
            segment['text'],
            lambda text: lm.tokenizer(text, add_special_tokens=True).input_ids,
            lm.tok_id_to_emb_id)
        with torch.inference_mode():
            # The official default task is the unchanged bare English caption.
            # Access raw IDs first: _decode_stream replaces empty outputs with
            # [0], whose VAE padding artefacts otherwise look like real motion.
            source_ids, source_mask = lm._tokenize(
                [model_input_text], labels=False, device=lm.language_model.main_lm.device)
            raw = lm.language_model.generate(
                input_ids=source_ids, attention_mask=source_mask, max_length=max_tokens)
            token_counts = require_motion_tokens({
                part: raw[key][0].detach().cpu().tolist()
                for part, key, _, _ in stream_specs
            }, valid_ids)
            streams = [lm._decode_stream(raw[key], prefix)[0]
                       for _, key, prefix, _ in stream_specs]
            limits = [96, 192, 192]
            streams = [stream.clamp(0, limit - 1) for stream, limit in zip(streams, limits)]
            decoded = [component.decode(stream) for component, stream in zip((body, left, right), streams)]
            frame_count = max(motion.shape[1] for motion in decoded)
            padded = [F.pad(motion, (0, 0, 0, frame_count-motion.shape[1]), mode='replicate') for motion in decoded]
            body_motion, left_motion, right_motion = padded
            normalized = torch.cat((body_motion[..., :30], left_motion, right_motion, body_motion[..., 30:]), dim=-1)[0]
            features = normalized * std + mean
        if features.ndim != 2 or features.shape[1] != 133 or not 1 <= frame_count <= 400:
            raise ValueError(f'Unexpected neural motion shape: {tuple(features.shape)}')
        if not torch.isfinite(features).all():
            raise ValueError('The model produced nonfinite motion parameters.')
        motion_variation = float(features[:, :120].std(dim=0, unbiased=False).max())
        if frame_count < 4 or motion_variation < 1e-6:
            raise ValueError('The model did not produce a usable changing motion sequence.')
        generation_seconds = time.perf_counter() - generated_at
        # The official How2Sign loader resamples RGB-derived poses to 24fps.
        # No generated frame is deleted and source-audio alignment is not claimed.
        fps = 24
        metadata = {
            'id': segment['id'], 'format': FEATURE_FORMAT, 'language': 'ASL', 'source_language': 'en',
            'model': 'MaDiS-How2Sign', 'source_commit': SOURCE_COMMIT,
            'model_revision': HF_REVISION, 'checkpoint_sha256': CHECKPOINT_SHA256,
            'license': 'CC-BY-NC-ND-4.0', 'text': segment['text'], 'fps': fps,
            'frame_count': frame_count, 'duration': frame_count/fps,
            'feature_layout': FEATURE_LAYOUT, 'model_load_seconds': round(load_seconds, 3),
            'generation_seconds': round(generation_seconds, 3), 'seed': seed,
            'max_tokens': max_tokens, 'motion_variation': motion_variation,
            'decoder_guard': DECODER_GUARD, 'valid_motion_tokens': token_counts,
            'input_normalization_version': INPUT_NORMALIZATION,
            'model_input_text': model_input_text, 'input_normalizations': input_normalizations,
            'input_case_normalized': 'lowercase_for_compact_vocabulary' in input_normalizations,
            'linguistically_verified': False, 'smpl_model_assets_used': False,
            'timing': 'How2Sign 24fps pose frame rate; generated motion is not word-aligned to source audio.',
        }
        target = output / f'{index:04d}' if batched else output
        target.mkdir(parents=True, exist_ok=True)
        motion_path, json_path = target / 'motion.npz', target / 'motion.json'
        np.savez_compressed(motion_path, features=features.cpu().numpy(),
                            normalized_features=normalized.cpu().numpy(),
                            body_tokens=streams[0].cpu().numpy(),
                            left_hand_tokens=streams[1].cpu().numpy(),
                            right_hand_tokens=streams[2].cpu().numpy(),
                            fps=np.array(fps), metadata=np.array(json.dumps(metadata)))
        json_path.write_text(json.dumps({**metadata, 'features': features.cpu().tolist()},
                                        ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
        (target / 'metadata.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
        result = {**metadata, 'motion_npz': str(motion_path), 'motion_json': str(json_path)}
        results.append(result)
        (output / 'index.json').write_text(json.dumps({'status': 'ready' if len(results)==len(segments) else 'processing',
                    'model': 'MaDiS-How2Sign', 'format': FEATURE_FORMAT,
                    'completed_segments': len(results), 'segment_count': len(segments), 'motions': results},
                    ensure_ascii=False, indent=2), encoding='utf-8')
        event('segment_completed', segment_id=segment['id'], segment_index=index,
              segment_count=len(segments), completed_segments=len(results), **result)
    event('completed', status='ready', index_json=str(output / 'index.json'),
          segment_count=len(results), model_load_seconds=round(load_seconds, 3),
          total_seconds=round(time.perf_counter()-started, 3), motions=results)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', type=Path, help='JSON file containing text, optional seed/max_tokens/threads.')
    parser.add_argument('--text', help='English text, as an alternative to --request.')
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--model-root', type=Path, default=Path(__file__).resolve().parents[2] / 'models' / 'MaDiS')
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args()
    try:
        if bool(args.request) == bool(args.text):
            raise ValueError('Provide exactly one of --request or --text.')
        request = json.loads(args.request.read_text(encoding='utf-8-sig')) if args.request else {'text': args.text}
        if not isinstance(request, dict):
            raise ValueError('The JSON request must be an object.')
        run(request, args.output_dir.resolve(), args.model_root.resolve())
    except Exception as error:
        event('failed', code='neural_inference_failed', message=str(error))
        if args.debug:
            import traceback
            traceback.print_exc(file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
