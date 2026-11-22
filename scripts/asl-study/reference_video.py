"""Show one realigned human performance and two avatar performances at native speed."""
import argparse
import json
import math
import os
import subprocess
from fractions import Fraction
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
PANEL = (372, 384)
FPS = 30


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def panels(clip, source, ffmpeg):
    width, height = clip['width'], clip['height']
    raw = subprocess.check_output([str(ffmpeg), '-v', 'error', '-i', str(source), '-an', '-sn',
                                   '-fps_mode', 'passthrough', '-f', 'rawvideo', '-pix_fmt', 'rgb24', 'pipe:1'])
    frames = np.frombuffer(raw, dtype=np.uint8).reshape(-1, height, width, 3)
    if len(frames) != len(clip['frames']):
        raise ValueError('Decoded frames and landmarks disagree')
    shoulders = np.array([frame['body'][:2] for frame in clip['frames'] if frame['body']
                          and min(j[2] for j in frame['body'][:2]) >= .5])
    center = np.median(shoulders[:, :, :2].mean(axis=1), axis=0)
    shoulder_span = np.median(np.linalg.norm(shoulders[:, 0, :2] - shoulders[:, 1, :2], axis=1))
    scale = 106 / shoulder_span
    x, y = center
    box = (x - 186 / scale, y - 140 / scale, x + 186 / scale, y + 244 / scale)
    return [Image.fromarray(frame).transform(PANEL, Image.Transform.EXTENT, box,
                                             Image.Resampling.BICUBIC, fillcolor='#111318')
            for frame in frames]


def make(original, study, ident):
    ffmpeg = next((ROOT / 'tools/ffmpeg').rglob('ffmpeg.exe'))
    rows = read(original / 'landmarks.json')['clips'] + read(study / 'landmarks.json')['clips']
    indexed = {(row['kind'], row['id']): row for row in rows}
    caption = next(s['text'] for s in read(study / 'samples.json') if s['id'] == ident)
    sources = [
        ('human', 'Haqiqiy ASL tarjimoni', original.parent / 'human' / f'{ident}.mp4'),
        ('avatar', 'Avatar · inglizcha matndan', original / 'avatar' / f'avatar-{ident}.mp4'),
        ('reference', 'Avatar · yozuv kodlaridan', study / 'avatar' / f'avatar-{ident}.mp4'),
    ]
    base = Image.new('RGB', (1160, 560), '#111823')
    draw = ImageDraw.Draw(base)
    fonts = Path(os.environ['WINDIR']) / 'Fonts'
    def font(size, bold=False):
        return ImageFont.truetype(str(fonts / ('segoeuib.ttf' if bold else 'segoeui.ttf')), size)
    draw.text((16, 10), f'{ident}-jumla. Qo‘l harakatini taqqoslash', font=font(27, True), fill='#fafcff')
    draw.text((16, 48), caption, font=font(19), fill='#c4d6e5')
    prepared = []
    for i, (kind, label, path) in enumerate(sources):
        clip = indexed[kind, ident]
        rate = float(Fraction(clip['fps']))
        frames = panels(clip, path, ffmpeg)
        x = 14 + 380 * i
        draw.text((x, 88), label, font=font(20, True), fill='#ecf3fa')
        draw.text((x, 501), (f'{len(frames)/rate:.2f} s').replace('.', ','), font=font(17), fill='#b8cfde')
        prepared.append((x, rate, frames))
    draw.text((14, 532), 'Ijrolar birga boshlanadi. Har biri o‘z tezligida ko‘rsatilgan.',
              font=font(15), fill='#c2d6e3')
    end_panel = Image.new('RGB', PANEL, '#17212d')
    ImageDraw.Draw(end_panel).text((PANEL[0] / 2, PANEL[1] / 2), 'Ijro tugadi',
                                   anchor='mm', font=font(20), fill='#cad8e2')
    output = study / f'uch-ijro-{ident}.mp4'
    temp = output.with_suffix('.tmp.mp4')
    count = math.ceil(max(len(frames) / rate for _, rate, frames in prepared) * FPS)
    # Use an early frame common to all three actual performances for the still.
    mid = int(min(len(frames) / rate for _, rate, frames in prepared) * FPS / 2)
    args = [str(ffmpeg), '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
            '-s', '1160x560', '-r', str(FPS), '-i', 'pipe:0', '-an', '-c:v', 'libx264',
            '-crf', '16', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(temp)]
    with subprocess.Popen(args, stdin=subprocess.PIPE) as writer:
        for tick in range(count):
            canvas = base.copy()
            for x, rate, frames in prepared:
                at = int(tick * rate / FPS)
                canvas.paste(frames[at] if at < len(frames) else end_panel, (x, 115))
            if tick == mid:
                canvas.save(study / f'uch-ijro-{ident}.jpg', quality=94)
            writer.stdin.write(canvas.tobytes())
        writer.stdin.close()
        if writer.wait():
            raise RuntimeError('Could not encode review MP4')
    temp.replace(output)
    print(f'{output} · {count} frames')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('original', type=Path)
    parser.add_argument('reconstructed', type=Path)
    parser.add_argument('id')
    args = parser.parse_args()
    make(args.original, args.reconstructed, args.id)
