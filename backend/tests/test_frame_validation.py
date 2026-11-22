"""PNG integrity tests use synthetic pixels, never sign-language fixtures."""
import struct
import zlib
import pytest
from backend.app.frame_validation import validate_png_frame, SIGNATURE


def chunk(kind, payload):
    return struct.pack('>I', len(payload)) + kind + payload + struct.pack('>I', zlib.crc32(payload, zlib.crc32(kind)) & 0xffffffff)


def png(width=384, height=512, channels=4, raw=None, compressed=None):
    header = chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6 if channels == 4 else 2, 0, 0, 0))
    if raw is None:raw = (b'\0' + bytes(width * channels)) * height
    data = chunk(b'IDAT', zlib.compress(raw) if compressed is None else compressed)
    return SIGNATURE + header + data + chunk(b'IEND', b'')


@pytest.mark.parametrize('size,channels', [((384, 512), 4), ((512, 384), 4), ((384, 512), 3)])
def test_accepts_canvas_and_rgb_fixture_formats_without_rewriting(size, channels):
    raw = png(*size, channels=channels)
    original = raw[:]
    assert validate_png_frame(raw, size) is None and raw == original


def test_header_only_fake_is_rejected():
    raw = SIGNATURE + struct.pack('>I', 13) + b'IHDR' + struct.pack('>II', 384, 512)
    with pytest.raises(ValueError):validate_png_frame(raw, (384, 512))


@pytest.mark.parametrize('mutation', [
    lambda p: p[:-1],
    lambda p: p + b'trailing',
    lambda p: p[:29] + bytes([p[29] ^ 1]) + p[30:],
    lambda p: p[:8] + chunk(b'IHDR', struct.pack('>IIBBBBB', 384, 512, 8, 6, 0, 0, 0)) + p[8:],
    lambda p: p[:-12] + chunk(b'IDAT', b'not another stream') + p[-12:],
])
def test_rejects_truncation_trailing_crc_duplicate_header_and_broken_idat(mutation):
    with pytest.raises(ValueError):validate_png_frame(mutation(png()), (384, 512))


def test_rejects_wrong_dimensions_invalid_filter_and_decompression_bomb():
    with pytest.raises(ValueError):validate_png_frame(png(), (512, 384))
    with pytest.raises(ValueError):validate_png_frame(png(raw=(b'\x05' + bytes(384 * 4)) * 512), (384, 512))
    with pytest.raises(ValueError):validate_png_frame(png(raw=bytes(8 * 1024 * 1024)), (384, 512))


def test_requires_complete_single_zlib_stream():
    payload = zlib.compress((b'\0' + bytes(384 * 4)) * 512)
    for stream in [payload[:-2], payload + b'extra', payload + payload]:
        with pytest.raises(ValueError):validate_png_frame(png(compressed=stream), (384, 512))


def test_rejects_interlace_animation_and_unknown_critical_chunks():
    header = chunk(b'IHDR', struct.pack('>IIBBBBB', 384, 512, 8, 6, 0, 0, 1))
    with pytest.raises(ValueError):validate_png_frame(SIGNATURE + header + png()[33:], (384, 512))
    for kind in [b'acTL', b'FOOB']:
        with pytest.raises(ValueError):validate_png_frame(png()[:33] + chunk(kind, b'') + png()[33:], (384, 512))


def test_rejects_frame_over_byte_limit():
    with pytest.raises(ValueError):validate_png_frame(png() + bytes(1024 * 1024), (384, 512))
