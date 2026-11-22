"""Bounded PNG validation before an uploaded frame reaches FFmpeg.

The browser and local frame tools produce single non-interlaced PNG images.
No pixels are changed here; chunk CRCs and the complete zlib scanline stream
are checked without loading an image library or accepting animated images.
"""
import struct
import zlib

MAX_FRAME_BYTES = 1024 * 1024
MAX_DECODED_BYTES = 4 * 1024 * 1024
SIGNATURE = b'\x89PNG\r\n\x1a\n'
DEPTHS = {0: {1, 2, 4, 8, 16}, 2: {8, 16}, 3: {1, 2, 4, 8}, 4: {8, 16}, 6: {8, 16}}
CHANNELS = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}


def validate_png_frame(raw, expected):
    """Return None for a complete safe PNG, otherwise raise ValueError.

    ``expected`` is the server-selected ``(width, height)``. The input remains
    unchanged. Interlaced and APNG inputs are deliberately unsupported because
    this endpoint stores one deterministic browser capture per timestamp.
    """
    if len(raw) > MAX_FRAME_BYTES:
        raise ValueError('PNG kadr hajmi 1 MB dan oshmasin.')
    if len(raw) < 45 or raw[:8] != SIGNATURE:
        raise ValueError('To‘liq PNG kadr talab qilinadi.')

    cursor = 8
    seen_header = seen_end = seen_palette = False
    seen_data = data_ended = False
    compressed = bytearray()
    row_bytes = decoded_size = color_type = bit_depth = 0
    while cursor < len(raw):
        if len(raw) - cursor < 12:
            raise ValueError('PNG bloki to‘liq emas.')
        length = struct.unpack_from('>I', raw, cursor)[0]
        kind = bytes(raw[cursor + 4:cursor + 8])
        if any(not (65 <= value <= 90 or 97 <= value <= 122) for value in kind) or kind[2] & 32:
            raise ValueError('PNG blok turi yaroqsiz.')
        end = cursor + 12 + length
        if end > len(raw):
            raise ValueError('PNG blok uzunligi yaroqsiz.')
        payload = memoryview(raw)[cursor + 8:cursor + 8 + length]
        checksum = struct.unpack_from('>I', raw, cursor + 8 + length)[0]
        crc = zlib.crc32(payload, zlib.crc32(kind)) & 0xffffffff
        if crc != checksum:
            raise ValueError('PNG kadr CRC tekshiruvidan o‘tmadi.')

        if not seen_header and kind != b'IHDR':
            raise ValueError('PNG sarlavhasi birinchi bo‘lishi kerak.')
        if kind == b'IHDR':
            if seen_header or length != 13:
                raise ValueError('PNG sarlavhasi yaroqsiz.')
            width, height, bit_depth, color_type, compression, filtering, interlace = struct.unpack('>IIBBBBB', payload)
            if (width, height) != tuple(expected) or width <= 0 or height <= 0:
                raise ValueError(f'Kadr {expected[0]}×{expected[1]} bo‘lishi kerak.')
            if color_type not in DEPTHS or bit_depth not in DEPTHS[color_type] or compression or filtering or interlace:
                raise ValueError('PNG rang formati yoki interlace qo‘llanmaydi.')
            row_bytes = (width * CHANNELS[color_type] * bit_depth + 7) // 8
            decoded_size = height * (row_bytes + 1)
            if decoded_size > MAX_DECODED_BYTES:
                raise ValueError('Ochilgan PNG kadr hajmi chegaradan katta.')
            seen_header = True
        elif kind == b'PLTE':
            if seen_palette or seen_data or color_type in {0, 4} or not length or length % 3 or length > 768:
                raise ValueError('PNG rang palitrasi yaroqsiz.')
            if color_type == 3 and length // 3 > 2 ** bit_depth:
                raise ValueError('PNG palitrasi bit chuqurligiga mos emas.')
            seen_palette = True
        elif kind == b'IDAT':
            if data_ended or color_type == 3 and not seen_palette:
                raise ValueError('PNG tasvir bloklari tartibi yaroqsiz.')
            seen_data = True
            compressed.extend(payload)
        elif kind == b'IEND':
            if length or not seen_data or end != len(raw):
                raise ValueError('PNG yakuni yoki ortiqcha ma’lumot yaroqsiz.')
            seen_end = True
            cursor = end
            break
        else:
            if kind in {b'acTL', b'fcTL', b'fdAT'}:
                raise ValueError('Animatsiyali PNG kadr qabul qilinmaydi.')
            if not kind[0] & 32:
                raise ValueError('Noma’lum majburiy PNG bloki.')
            if seen_data:
                data_ended = True
        cursor = end

    if not seen_end or not compressed:
        raise ValueError('PNG tasviri yoki yakuni yo‘q.')
    try:
        inflater = zlib.decompressobj()
        pixels = inflater.decompress(compressed, decoded_size + 1)
    except zlib.error as exc:
        raise ValueError('PNG siqilgan tasviri buzilgan.') from exc
    if len(pixels) != decoded_size or not inflater.eof or inflater.unused_data or inflater.unconsumed_tail:
        raise ValueError('PNG tasviri uzunligi yoki zlib yakuni yaroqsiz.')
    if any(pixels[offset] > 4 for offset in range(0, decoded_size, row_bytes + 1)):
        raise ValueError('PNG qator filtri yaroqsiz.')
