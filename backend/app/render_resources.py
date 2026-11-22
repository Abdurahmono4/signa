"""Conservative scratch-space estimate, not a filesystem reservation."""
import shutil

MIB=1024*1024
MIN_FREE_BYTES=512*MIB

def required_render_bytes(frames,duration):
    # Each accepted PNG is capped at 1 MiB. Also budget 2 MiB/output second
    # for the encoded MP4 plus a 512 MiB filesystem safety margin.
    return max(0,frames)*MIB+int(max(0,duration)*2*MIB)+MIN_FREE_BYTES

def ensure_render_space(path,frames,duration):
    required=required_render_bytes(frames,duration)
    if shutil.disk_usage(path).free<required:
        raise ValueError(f'Video eksporti uchun diskda yetarli joy yo‘q. Taxminan {required/MIB:.0f} MB bo‘sh joy kerak. Joy bo‘shatib qayta urinib ko‘ring.')
    return required
