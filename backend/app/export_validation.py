"""Validate individual output streams; container duration can hide a short video/audio track."""
import math
from fractions import Fraction


def _number(value, label):
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f'{label} aniqlanmadi.') from exc
    if not math.isfinite(number) or number <= 0:
        raise RuntimeError(f'{label} yaroqsiz.')
    return number


def validate_export(info, duration, width, height, source_info, timing_scale=1., expected_fps=24):
    streams = info.get('streams', [])
    video = [s for s in streams if s.get('codec_type') == 'video']
    audio = [s for s in streams if s.get('codec_type') == 'audio']
    if len(video) != 1 or len(audio) != 1:
        raise RuntimeError('Natijada bitta video va bitta audio yo‘lagi bo‘lishi kerak.')
    v, a = video[0], audio[0]
    if v.get('codec_name') != 'h264' or a.get('codec_name') != 'aac':
        raise RuntimeError('MP4 kodeklari tekshiruvi o‘tmadi.')
    if (v.get('width'), v.get('height')) != (width, height) or v.get('pix_fmt') != 'yuv420p':
        raise RuntimeError('Natija o‘lchami yoki rang formati mos emas.')
    try:
        fps = float(Fraction(v.get('avg_frame_rate', '0/1')))
    except (ValueError, ZeroDivisionError, TypeError) as exc:
        raise RuntimeError('Natija kadr tezligi aniqlanmadi.') from exc
    if abs(fps - expected_fps) > .01:
        raise RuntimeError(f'Natija {expected_fps} kadr/soniya formatiga mos emas.')
    video_duration = _number(v.get('duration'), 'Video davomiyligi')
    audio_duration = _number(a.get('duration'), 'Audio davomiyligi')
    frames = _number(v.get('nb_frames'), 'Kadrlar soni')
    if abs(video_duration - duration) > .125 or abs(frames - duration * expected_fps) > 2:
        raise RuntimeError('Natijadagi video yoki avatar kadrlari to‘liq emas.')
    if abs(_number(info.get('format', {}).get('duration'), 'MP4 davomiyligi') - duration) > .5:
        raise RuntimeError('Natija davomiyligi mos emas.')
    source_audio = next((s for s in source_info.get('streams', []) if s.get('codec_type') == 'audio'), None)
    if source_audio is None:
        raise RuntimeError('Asl audio yo‘lagi topilmadi.')
    source_duration = source_audio.get('duration')
    known_audio_duration = source_duration not in (None, 'N/A')
    expected_audio = min(duration, _number(source_duration, 'Asl audio davomiyligi') * timing_scale) if known_audio_duration else duration
    # AAC encoder padding and container rounding are allowed; substantial truncation is not.
    if (known_audio_duration and abs(audio_duration - expected_audio) > .25) or audio_duration > duration + .25:
        raise RuntimeError('Natijadagi audio davomiyligi asl audioga mos emas.')
    return {'duration':info['format']['duration'], 'codecs':['h264','aac'],
            'width':width, 'height':height, 'fps':fps, 'frames':int(frames),
            'video_duration':video_duration, 'audio_duration':audio_duration,
            'audio_duration_reference':'source-stream' if known_audio_duration else 'container-upper-bound',
            'validation':'streams-v1'}
