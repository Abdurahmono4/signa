"""Local MaDiS generation queue, kept separate from the speech environment."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import queue
import re
import subprocess
import threading
import time

MODEL_REVISION = 'ceaed59c964820f2c13401a0870b2988686956ad'
CACHE_VERSION = 'signa-madis-plan-v3-input-normalization'
_guard = threading.Lock()
_states: dict[str, dict] = {}
_cancel: dict[str, threading.Event] = {}
_processes: dict[str, subprocess.Popen] = {}


def stop_process(process):
    if process.poll() is not None:
        return
    if os.name == 'nt':
        # The Windows venv executable can launch a base-Python child. Stop the
        # tree owned by this inference request so cancellation leaves no worker.
        try:
            result = subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0), timeout=15)
            if result.returncode and process.poll() is None:
                process.terminate()
        except (OSError, subprocess.TimeoutExpired):
            if process.poll() is None:
                process.terminate()
    else:
        process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)


def shutdown():
    with _guard:
        for event in _cancel.values():
            event.set()
        processes = list(_processes.values())
    for process in processes:
        stop_process(process)


def readiness(root: Path):
    base = root / 'models' / 'MaDiS'
    required = {
        'sft_how2sign.ckpt': 6295891758,
        'Qwen3-0.6B-Base-en-zh-de.zip': 902653548,
        'mean.pt': 1909, 'std.pt': 1904,
    }
    missing = [name for name, size in required.items()
               if not (base / 'assets' / name).is_file()
               or (base / 'assets' / name).stat().st_size != size]
    runtime = base / 'runtime'
    if not (runtime / '.signa-ready.json').is_file() or not (runtime / '.venv' / 'Scripts' / 'python.exe').is_file():
        missing.append('CPU runtime')
    if not (base / 'source' / 'mGPT' / 'archs' / 'madis.py').is_file():
        missing.append('MaDiS source')
    qwen = base / 'assets' / 'Qwen3-0.6B-Base-en-zh-de'
    if not all((qwen / name).is_file() for name in ['config.json', 'pytorch_model.bin', 'tokenizer.json', 'map_ids.pkl']):
        missing.append('Qwen extraction')
    downloaded = 0
    newest = 0.
    for name, size in required.items():
        target = base / 'assets' / name
        if target.is_file() and target.stat().st_size == size:
            downloaded += size
            continue
        parts = base / 'assets' / 'range-parts' / name
        if parts.is_dir():
            entries = [part.stat() for part in parts.glob('*.part')]
            downloaded += min(size, sum(part.st_size for part in entries))
            newest = max([newest] + [part.st_mtime for part in entries])
    return {'ready': not missing, 'model': 'MaDiS-How2Sign',
            'revision': MODEL_REVISION, 'device': 'cpu', 'missing': missing,
            'installing': bool(missing) and time.time()-newest < 180,
            'downloaded_bytes': downloaded, 'total_bytes': sum(required.values())}


def chunks(segments):
    """Keep sentences together, with bounded inputs and estimated source timing."""
    result = []
    for index, segment in enumerate(segments):
        text = str(segment.get('text', '')).strip()
        words = text.split()
        if not words:
            continue
        aligned = segment.get('words') or []
        aligned_text = ' '.join(str(word.get('word', '')).strip() for word in aligned)
        if aligned and ' '.join(aligned_text.split()) == ' '.join(text.split()):
            group = []
            def add_group():
                if group:
                    result.append({'id': str(len(result)), 'text': ' '.join(str(w['word']).strip() for w in group),
                        'start': float(group[0]['start']), 'end': float(group[-1]['end']),
                        'segment_index': index})
            for word in aligned:
                if group and (float(word['start'])-float(group[-1]['end']) >= .5
                              or re.search(r'[.!?]$', str(group[-1]['word']).strip())
                              or len(group) >= 40):
                    add_group()
                    group = []
                group.append(word)
            add_group()
            continue
        phrases = re.split(r'(?<=[.!?])\s+', text)
        groups = []
        for phrase in phrases:
            tokens = phrase.split()
            while tokens:
                groups.append(' '.join(tokens[:40]))
                tokens = tokens[40:]
        start, end = float(segment['start']), float(segment['end'])
        cursor = start
        consumed = 0
        for phrase in groups:
            consumed += len(phrase.split())
            finish = start + (end-start) * consumed / len(words)
            result.append({'id': str(len(result)), 'text': phrase,
                           'start': cursor, 'end': finish, 'segment_index': index})
            cursor = finish
    merged = []
    for item in result:
        previous = merged[-1] if merged else None
        if (previous and item['start']-previous['end'] < .5
                and not re.search(r'[.!?]$', previous['text'])
                and item['end']-previous['start'] <= 16
                and len(previous['text'].split())+len(item['text'].split()) <= 40):
            previous['text'] += ' ' + item['text']
            previous['end'] = item['end']
        else:
            merged.append(dict(item))
    for index, item in enumerate(merged):
        item['id'] = str(index)
    return merged


def key_for(row):
    value = json.dumps([row['id'], row['revision'], row['segments'], MODEL_REVISION, CACHE_VERSION],
                       ensure_ascii=False, separators=(',', ':'))
    return hashlib.sha256(value.encode()).hexdigest()[:32]


def folder(data, row):
    return data / 'neural' / key_for(row)


def status(data, row):
    key = key_for(row)
    with _guard:
        state = _states.get(key)
        if state:
            return dict(state)
    path = folder(data, row) / 'plan.json'
    if path.is_file():
        return {'status': 'ready', 'phase': 'ready', 'progress': 100, 'key': key}
    return {'status': 'idle', 'phase': 'idle', 'progress': 0, 'key': key}


def enqueue(root, data, row, worker_lock, before_load):
    key = key_for(row)
    with _guard:
        existing = _states.get(key, {})
        if existing.get('status') in {'queued', 'processing'}:
            return dict(existing)
        if (folder(data, row) / 'plan.json').is_file():
            return {'status': 'ready', 'phase': 'ready', 'progress': 100, 'key': key}
        if any(state['status'] in {'queued', 'processing'} for state in _states.values()):
            raise RuntimeError('Boshqa avatar tayyorlanmoqda. Yakunlanishini kuting.')
        state = {'status': 'queued', 'phase': 'queued', 'progress': 0, 'key': key}
        _states[key] = state
        stop = _cancel[key] = threading.Event()
    thread = threading.Thread(target=_generate,
        args=(root, data, dict(row), worker_lock, before_load, stop), daemon=True)
    thread.start()
    return dict(state)


def cancel(row):
    with _guard:
        event = _cancel.get(key_for(row))
        if event:
            event.set()
            return True
    return False


def _generate(root, data, row, worker_lock, before_load, stop):
    key = key_for(row)
    out = folder(data, row)
    out.mkdir(parents=True, exist_ok=True)
    process = None
    def update(**values):
        with _guard:
            _states[key].update(values)
    try:
        segments = chunks(json.loads(row['segments'] or '[]'))
        if not segments:
            raise ValueError('Nutq matni bo‘sh. Nutqli video yoki audio tanlang.')
        request = out / 'request.json'
        request.write_text(json.dumps({'segments': [{'id': s['id'], 'text': s['text']} for s in segments],
                                      'max_tokens': 100, 'threads': 8, 'seed': 1234}), encoding='utf-8')
        with worker_lock:
            if stop.is_set():
                raise InterruptedError()
            before_load()
            update(status='processing', phase='loading_model', progress=2)
            base = root / 'models' / 'MaDiS'
            command = [str(base / 'runtime' / '.venv' / 'Scripts' / 'python.exe'),
                       str(root / 'app' / 'inference' / 'madis_runner.py'),
                       '--request', str(request), '--output-dir', str(out / 'motion'), '--debug']
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding='utf-8', errors='replace', creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            with _guard:
                _processes[key] = process
            lines = queue.Queue()
            def read_output():
                for line in process.stdout:
                    lines.put(line)
            threading.Thread(target=read_output, daemon=True).start()
            started = time.monotonic()
            log = []
            failure_message = ''
            while process.poll() is None or not lines.empty():
                if stop.is_set():
                    raise InterruptedError()
                if time.monotonic()-started > max(1800, 300*len(segments)):
                    raise TimeoutError('Avatar tayyorlash vaqti tugadi. Qisqaroq video bilan sinang.')
                try:
                    line = lines.get(timeout=.25)
                except queue.Empty:
                    continue
                log.append(line)
                log = log[-200:]
                try:
                    event = json.loads(line)
                    if event.get('event') == 'progress':
                        update(phase=event.get('stage', 'generating_motion'),
                               progress=min(95, max(5, round(5+90*event.get('completed_segments', 0)/len(segments)))))
                    elif event.get('event') == 'failed':
                        failure_message = str(event.get('message', ''))
                except (ValueError, TypeError):
                    pass
            (out / 'inference.log').write_text(''.join(log), encoding='utf-8')
            if process.returncode:
                if 'ishora tokenlarini' in failure_message or 'motion tokens' in failure_message:
                    raise RuntimeError('ASL modeli bu gap uchun harakat yarata olmadi. Nutq matnini tekshirib qayta urinib ko‘ring.')
                if 'Unsupported text tokens' in failure_message:
                    raise RuntimeError('Matndagi ayrim so‘zlar ASL modelining matn lug‘atida yo‘q. Nutq matnini tekshirish kerak.')
                raise RuntimeError('ASL modeli ishga tushmadi. Model jurnalini tekshirish kerak.')
        index = json.loads((out / 'motion' / 'index.json').read_text(encoding='utf-8'))
        if index.get('status') != 'ready':
            raise ValueError('Model barcha gaplar uchun ijroni yakunlamadi.')
        if stop.is_set():
            raise InterruptedError()
        plan = build_plan(row, segments, index['motions'], key)
        temp = out / 'plan.tmp'
        temp.write_text(json.dumps(plan, ensure_ascii=False), encoding='utf-8')
        temp.replace(out / 'plan.json')
        update(status='ready', phase='ready', progress=100)
    except InterruptedError:
        update(status='cancelled', phase='cancelled', error='Avatar tayyorlash bekor qilindi.')
    except Exception as exc:
        update(status='failed', phase='failed', error=str(exc))
    finally:
        try:
            if process:
                stop_process(process)
        finally:
            with _guard:
                _cancel.pop(key, None)
                _processes.pop(key, None)


def build_plan(row, segments, motions, key):
    by_id = {str(m['id']): m for m in motions}
    items = []
    position = 0.
    source_cursor = 0.
    def append(text, start, end, clip=None, segment_index=None):
        nonlocal position
        span = max(0., end-start)
        motion_duration = float(clip['duration']) if clip else 0.
        rate = min(1.25, motion_duration/span) if clip and span > 0 else 1.
        rate = max(1., rate)
        duration = motion_duration/rate
        slot = max(span, duration)
        if slot <= 0:
            return
        items.append({'rendering': 'sign' if clip else 'gap', 'word_text': text,
            'letter': None, 'segment_index': segment_index, 'start': start, 'end': end,
            'text': text, 'status': 'generated' if clip else 'gap', 'sync_status': 'estimated',
            'timing': 'estimated' if clip else 'gap', 'word_count': len(text.split()), 'clip': clip,
            'media_start': start, 'media_end': end, 'media_play_start': start, 'media_play_end': end,
            'duration': duration, 'slot_duration': slot, 'hold_duration': max(0., slot-span),
            'playback_start': position, 'playback_end': position+slot,
            'clip_start': 0., 'clip_end': motion_duration, 'playback_rate': rate})
        position += slot
    for segment in segments:
        motion = by_id.get(segment['id'])
        if motion is None or not 0 < float(motion.get('duration', 0)) <= 20:
            raise ValueError('Model barcha nutq bo‘laklari uchun harakat qaytarmadi.')
        start = max(source_cursor, min(float(row['duration']), float(segment['start'])))
        end = max(start, min(float(row['duration']), float(segment['end'])))
        if start > source_cursor:
            append('', source_cursor, start)
        clip = {'id': f'neural-{key}-{segment["id"]}', 'phrase': segment['text'],
            'duration': float(motion['duration']), 'keyframes': [], 'status': 'model_generated',
            'source': 'MaDiS-How2Sign', 'license': 'CC-BY-NC-ND-4.0',
            'neural_asset': f'/api/jobs/{row["id"]}/neural/motions/{segment["id"]}?key={key}'}
        append(segment['text'], start, end, clip, segment['segment_index'])
        source_cursor = end
    if source_cursor < float(row['duration']):
        append('', source_cursor, float(row['duration']))
    total_words = sum(len(s['text'].split()) for s in segments)
    return {'job_id': row['id'], 'revision': row['revision'], 'mode': 'neural_asl',
        'playback': 'paced', 'language': 'ASL', 'input_language': 'en',
        'presentation': 'sentences', 'fingerspelling_enabled': False,
        'complete_translation': False, 'source_preview_enabled': True,
        'media_duration': row['duration'], 'playback_duration': position,
        'hold_duration': position-float(row['duration']), 'items': items,
        'playable_signs': len(segments), 'matched': len(segments), 'source_previews': 0,
        'total_words': total_words, 'signed_words': total_words, 'spelled_words': 0,
        'caption_words': 0, 'fingerspelling_letters': 0, 'dictionary_missing_words': [],
        'missing_words': [], 'limitations': ['Model yaratgan ASL ijrosi; ASL mutaxassisi tekshiruvi talab etiladi.',
            'Nutq va ishora vaqti taxminiy moslangan.'],
        'spelling_limits': {'max_word_length': 0, 'max_letters': 0, 'max_added_seconds': 0, 'limited_words': []}}
