"""Deterministic global pacing: preserve every frame instead of rushing long signs."""
def motion_time_scale(items,max_rate=1.25):
    required=1.
    for item in items:
        if not item.get('supported'):continue
        span=item['end']-item['start']
        if span<=0:raise ValueError('Harakat uchun nutq oralig‘i yaroqsiz.')
        required=max(required,(item.get('duration_ms') or 0)/1000/span/max_rate)
    if required>4:
        raise ValueError('Harakat nutqdan juda uzun: 4× dan ko‘p sekinlatish kerak. Qisqaroq gap bilan qayta tayyorlang.')
    return required

def tempo_filters(scale):
    tempo=1/scale;filters=[]
    while tempo<.5:
        filters.append('atempo=0.5');tempo/=.5
    filters.append(f'atempo={tempo:.10f}')
    return ','.join(filters)

def rocketbox_capture_fps(items):
    """MaDiS emits 24 poses/s; at up to 1.25x playback they need 30 samples/s."""
    for item in items:
        if item.get('supported') and item.get('duration_ms', 0) > (item['end'] - item['start']) * 1000 + .5:
            return 30
    return 24
