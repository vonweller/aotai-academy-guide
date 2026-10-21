# -*- coding: utf-8 -*-
"""生成 A4 打印卡片：人脸样张 + 三件古物认物卡 + 使用说明。"""
import os
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(ROOT, '07_打印卡片')
DPI = 300
A4 = (int(8.27 * DPI), int(11.69 * DPI))
FONT_B = 'C:/Windows/Fonts/msyhbd.ttc'
FONT_R = 'C:/Windows/Fonts/msyh.ttc'


def font(path, size):
    return ImageFont.truetype(path, size)


def center_text(d, box, text, f, fill):
    x0, y0, x1, y1 = box
    w = d.textlength(text, font=f)
    asc, desc = f.getmetrics()
    h = asc + desc
    d.text(((x0 + x1 - w) / 2, (y0 + y1 - h) / 2), text, font=f, fill=fill)


def crop_marks(d, box, color=(0, 0, 0), ln=90, gap=14):
    x0, y0, x1, y1 = box
    for (cx, cy, dx, dy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        d.line([(cx, cy), (cx + dx * ln, cy)], fill=color, width=3)
        d.line([(cx, cy), (cx, cy + dy * ln)], fill=color, width=3)


def make_face_card():
    src = os.path.join(ROOT, '02_数据', 'data_pack', 'faces', 'print_visitor.jpg')
    img = Image.new('RGB', A4, 'white')
    d = ImageDraw.Draw(img)
    W, H = A4
    f_title = font(FONT_B, 74)
    f_sub = font(FONT_R, 40)
    f_tip = font(FONT_R, 34)
    f_small = font(FONT_R, 26)

    center_text(d, (0, 70, W, 170), '鳌台书院 · 预约访客', f_title, (30, 30, 30))
    center_text(d, (0, 175, W, 235), '人脸识别样张（打印后对着 CyberCAM 镜头）', f_sub, (90, 90, 90))

    side = 1500
    x0 = (W - side) // 2
    y0 = 300
    face = Image.open(src).convert('L')
    face = face.resize((side, side), Image.LANCZOS)
    img.paste(face.convert('RGB'), (x0, y0))
    d.rectangle([x0, y0, x0 + side, y0 + side], outline=(0, 0, 0), width=4)
    crop_marks(d, (x0, y0, x0 + side, y0 + side))

    y = y0 + side + 70
    tips = [
        '使用方法',
        '1. 用 A4 纸彩色打印，不要缩放，按裁切线剪下',
        '2. 正对 CyberCAM 镜头，距离 40–80 cm',
        '3. 第一关看到「识别成功」即可进入下一关',
    ]
    for i, t in enumerate(tips):
        f = f_tip if i == 0 else f_small
        d.text((150, y), t, font=f, fill=(40, 40, 40) if i == 0 else (70, 70, 70))
        y += 66 if i == 0 else 50

    d.text((150, H - 90), '图片来源 Wikimedia Commons，许可 CC BY-SA 2.0',
           font=f_small, fill=(150, 150, 150))

    os.makedirs(os.path.join(OUT, '01_人脸样张'), exist_ok=True)
    p = os.path.join(OUT, '01_人脸样张', 'A4_预约访客_人脸样张.jpg')
    img.save(p, quality=95, dpi=(DPI, DPI))
    print('saved', p)


if __name__ == '__main__':
    make_face_card()