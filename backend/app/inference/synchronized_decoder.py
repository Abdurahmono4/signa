"""Part-aligned decoding with explicit final-pose holds."""
PARTS = ('body', 'left_hand', 'right_hand')
DECODER_GUARD = 'aligned-tail-hold-v3'

def decode_aligned(raw, code_maps, eos):
    streams = [list(raw[p]) for p in PARTS]
    if not streams[0] or any(len(s) != len(streams[0]) for s in streams):
        raise ValueError('Modelning tana va qo‘l oqimlari bir xil uzunlikda emas.')
    try:
        end = streams[0].index(eos)
    except ValueError as exc:
        raise ValueError('Model ijroni yakunlamadi; kesilgan harakat qabul qilinmadi.') from exc
    if end == 0:
        raise ValueError('Model bo‘sh harakat yaratdi.')
    decoded = {}
    for part, stream in zip(PARTS, streams):
        if any(t != eos for t in stream[end:]):
            raise ValueError('Tana va qo‘llarning yakun vaqti mos emas.')
        mapping = code_maps[part]
        lane = stream[:end]
        stop = lane.index(eos) if eos in lane else end
        if not stop or any(t != eos for t in lane[stop:]) or any(t not in mapping for t in lane[:stop]):
            raise ValueError('Harakat o‘rtasida yaroqsiz token bor; vaqt siljitilmadi.')
        decoded[part] = [mapping[t] for t in lane[:stop]]
    return decoded
