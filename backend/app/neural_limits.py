"""One bounded motion budget used before generation and by the browser."""
MAX_MOTION_CHUNKS=75
MAX_MOTION_FRAMES=30000

def limits():return {'max_chunks':MAX_MOTION_CHUNKS,'max_frames':MAX_MOTION_FRAMES}

def check_chunks(count):
    if count>MAX_MOTION_CHUNKS:
        raise ValueError(f'Avatar uchun {count} ta ibora ajratildi. Hozir bir ishda {MAX_MOTION_CHUNKS} tagacha ibora qo‘llanadi; videoni qisqaroq bo‘laklarga ajrating. Matn va subtitrni saqlashingiz mumkin.')
