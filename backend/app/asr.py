"""Full-timeline ASR with overlapping context, word alignment and gap auditing.

VAD is evidence for the audit, never a destructive preprocessing filter.
Processed timeline coverage is NOT a transcription accuracy estimate.
"""
from dataclasses import dataclass
import math
from pathlib import Path
import re

import av
import numpy as np

RATE = 16000
CORE = 24.0
CONTEXT = 3.0


class Cancelled(Exception):
    pass


@dataclass
class Window:
    start: float
    end: float
    core_start: float
    core_end: float


def windows(duration, core=CORE, context=CONTEXT):
    return [Window(max(0, start-context), min(duration, start+core+context),
                   start, min(duration, start+core))
            for start in np.arange(0, duration, core).tolist()]


def decode_timeline(path, max_seconds=1200):
    """Decode all frames, preserving presentation gaps and audio/video offsets.

    Unlike faster_whisper.decode_audio, corrupt frames are not silently skipped.
    """
    chunks = []
    cursor = 0
    with av.open(str(path)) as container:
        origin = (container.start_time or 0) / av.time_base
        declared = (container.duration or 0) / av.time_base
        resampler = av.AudioResampler(format='fltp', layout='mono', rate=RATE)
        for decoded in container.decode(audio=0):
            for frame in resampler.resample(decoded):
                data = frame.to_ndarray().reshape(-1).astype(np.float32)
                position = round((float(frame.pts * frame.time_base)-origin) * RATE) if frame.pts is not None else cursor
                if position < 0:
                    data = data[-position:]
                    position = 0
                if position + len(data) > (max_seconds+1)*RATE:
                    raise ValueError('Decoded duration exceeds limit')
                chunks.append((position, data))
                cursor = max(cursor, position + len(data))
        for frame in resampler.resample(None):
            data = frame.to_ndarray().reshape(-1).astype(np.float32)
            chunks.append((cursor, data))
            cursor += len(data)
    if not chunks:
        raise ValueError('No audio frames decoded')
    total = max(cursor, round(min(declared, max_seconds)*RATE))
    audio = np.zeros(total, dtype=np.float32)
    for position, data in chunks:
        audio[position:position+len(data)] = data
    if not np.all(np.isfinite(audio)):
        raise ValueError('Non-finite audio samples')
    return audio, {'decoded_audio_end':round(cursor/RATE,3), 'timeline_seconds':round(total/RATE,3)}


def normalize(audio):
    if not len(audio):
        return audio
    peak = float(np.max(np.abs(audio)))
    rms = float(np.sqrt(np.mean(audio**2)))
    gain = min(8.0, .06/max(rms, 1e-9), .98/max(peak, 1e-9))
    return (audio * max(1.0, gain)).astype(np.float32)


def recognize(model, audio, offset, core_start, core_end, source, recovery=False):
    if len(audio) == 0 or float(np.max(np.abs(audio))) < 1e-7:
        return []
    segments, _ = model.transcribe(
        normalize(audio), language='en', beam_size=5, best_of=5,
        temperature=(0.0, 0.2, 0.4), vad_filter=False,
        word_timestamps=True, condition_on_previous_text=False,
        no_speech_threshold=None, compression_ratio_threshold=2.4,
        log_prob_threshold=-1.0, suppress_blank=True,
    )
    words = []
    for segment in segments:
        aligned = getattr(segment, 'words', None)
        if not aligned:
            # Preserve text if the aligner provides no words; flag for manual review.
            aligned = [type('Unaligned', (), dict(start=segment.start, end=segment.end,
                       word=segment.text, probability=0.0))()]
        for word in aligned:
            start = float(offset + word.start)
            end = min(float(offset + word.end), offset+len(audio)/RATE)
            middle = (start+end)/2
            if not (core_start <= middle < core_end) or not word.word.strip():
                continue
            if recovery and (word.probability < .35 or segment.avg_logprob < -1.5):
                continue
            words.append({'start':round(max(0,start),3), 'end':round(max(start+.001,end),3),
                          'word':word.word, 'probability':round(float(word.probability),3),
                          'needs_review':bool(recovery or word.probability < .45 or segment.avg_logprob < -1),
                          'source':source, 'recovered':recovery})
    return words


def deduplicate(words):
    """Only suppress coincident hypotheses from DIFFERENT decode windows.

    Consecutive real repetitions from the same pass must remain intact.
    """
    result = []
    for word in sorted(words, key=lambda w:(w['start'],w['end'])):
        token = re.sub(r'\W','',word['word']).lower()
        duplicate = None
        for previous in result[-8:]:
            overlap = min(previous['end'],word['end'])-max(previous['start'],word['start'])
            if (previous['source'] != word['source'] and overlap > 0 and
                    re.sub(r'\W','',previous['word']).lower() == token and token):
                duplicate = previous
                break
        if duplicate is None:
            result.append(word)
        elif word['probability'] > duplicate['probability']:
            result[result.index(duplicate)] = word
    return sorted(result,key=lambda w:w['start'])


def group_words(words):
    segments, bucket = [], []
    def flush():
        if bucket:
            segments.append({'start':bucket[0]['start'], 'end':max(w['end'] for w in bucket),
                             'text':''.join(w['word'] for w in bucket).strip(),
                             'needs_review':any(w['needs_review'] for w in bucket),
                             'words':[dict(w) for w in bucket], 'edited':False})
            bucket.clear()
    for word in words:
        if bucket and (word['start']-bucket[-1]['end'] > 1.2 or
                       word['end']-bucket[0]['start'] > 7 or len(bucket) >= 14):
            flush()
        bucket.append(word)
        if re.search(r'[.!?]["\u201d]?$',word['word'].strip()):
            flush()
    flush()
    return segments


def find_gaps(activity, words, duration, minimum=1.4):
    """Find active spans without word coverage, using 100ms audit bins."""
    bins = int(math.ceil(duration*10))
    active, covered = np.zeros(bins,dtype=bool), np.zeros(bins,dtype=bool)
    for start,end in activity:
        active[max(0,int(start*10)):min(bins,math.ceil(end*10))] = True
    for word in words:
        covered[max(0,int((word['start']-.25)*10)):min(bins,math.ceil((word['end']+.25)*10))] = True
    missing = active & ~covered
    spans, start = [], None
    for index, value in enumerate(np.r_[missing, False]):
        if value and start is None:
            start = index
        elif not value and start is not None:
            if (index-start)/10 >= minimum:
                spans.append({'start':start/10,'end':min(duration,index/10),
                              'reason':'Faol audio bor, lekin matn aniqlanmagan. Tinglab tekshiring.'})
            start = None
    return spans


def activity_intervals(audio, mode):
    if mode == 'music':
        # Acoustic activity, not a claim that instruments are speech.
        hop = RATE//10
        return [(i/RATE,min(len(audio),i+hop)/RATE) for i in range(0,len(audio),hop)
                if np.sqrt(np.mean(audio[i:i+hop]**2)) > .003]
    from faster_whisper.vad import get_speech_timestamps, VadOptions
    detected = get_speech_timestamps(audio, VadOptions(threshold=.25, min_speech_duration_ms=100,
                                      min_silence_duration_ms=300,speech_pad_ms=100))
    return [(s['start']/RATE,s['end']/RATE) for s in detected]


def run_pipeline(model, path, mode='speech', progress=lambda *args:None, cancelled=lambda:False):
    progress('decoding', 2, [], {})
    audio, metadata = decode_timeline(path)
    duration = len(audio)/RATE
    schedule = windows(duration)
    words, processed = [], []
    for index, window in enumerate(schedule):
        if cancelled():
            raise Cancelled()
        progress('transcribing', 5+int(70*index/len(schedule)), group_words(words), metadata)
        words.extend(recognize(model, audio[round(window.start*RATE):round(window.end*RATE)],
                               window.start, window.core_start, window.core_end, f'chunk-{index}'))
        words = deduplicate(words)
        processed.append([window.core_start,window.core_end])
    progress('auditing', 77, group_words(words), metadata)
    if cancelled():
        raise Cancelled()
    warnings = []
    try:
        activity = activity_intervals(audio, mode)
    except Exception:
        activity = []
        warnings.append('Audio faolligi auditi bajarilmadi; matn to‘liqligini qo‘lda tekshiring.')
    initial_gaps = find_gaps(activity,words,duration)
    targets = []
    for gap in initial_gaps:
        for start in np.arange(gap['start'],gap['end'],18):
            targets.append((float(start),min(gap['end'],float(start)+18)))
    # Bound the extra compute. Remaining spans are visible, never silently hidden.
    targets = sorted(targets,key=lambda pair:pair[1]-pair[0],reverse=True)[:6]
    recovered = 0
    for index,(start,end) in enumerate(targets):
        if cancelled():
            raise Cancelled()
        progress('recovering',80+int(17*index/max(1,len(targets))),group_words(words),metadata)
        context_start,context_end = max(0,start-2),min(duration,end+2)
        candidates = recognize(model,audio[round(context_start*RATE):round(context_end*RATE)],
                               context_start,start,end,f'recovery-{index}',recovery=True)
        recovered += len(candidates)
        words = deduplicate(words+candidates)
    gaps = find_gaps(activity,words,duration)
    if mode == 'music':
        warnings.append('Qo‘shiq/musiqada cholg‘u va cho‘zilgan tovushlar ham faol audio deb belgilanadi. Matnni tekshiring.')
    if not words:
        warnings.append('Matn aniqlanmadi. Bu audioda nutq yo‘q degani emas.')
    report = {**metadata,'processed_seconds':round(sum(end-start for start,end in processed),3),
              'processed_ranges':processed,'chunks':len(schedule),'retry_count':len(targets),
              'recovered_words':recovered,'suspect_spans':gaps,'warnings':warnings,
              'review_words':sum(w['needs_review'] for w in words),'word_count':len(words),
              'mode':mode,'algorithm':'overlap-audit-v2', 'complete_timeline':True}
    return group_words(words),report
