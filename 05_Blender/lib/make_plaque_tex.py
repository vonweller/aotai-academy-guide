# -*- coding: utf-8 -*-
"""生成匾额/楹联贴图（用宿主 Python + Pillow，Blender 自带 Python 无 PIL）

输出：05_Blender/tex/*.png
"""
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "tex")
os.makedirs(OUT, exist_ok=True)

FONTS = ["C:/Windows/Fonts/simkai.ttf", "C:/Windows/Fonts/STKAITI.TTF",
         "C:/Windows/Fonts/simhei.ttf", "C:/Windows/Fonts/msyh.ttc"]
GOLD = (214, 170, 80)
BG = (18, 26, 32)


def font(size):
    for fp in FONTS:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                pass
    return ImageFont.load_default()


def plaque(text, out, w=1024, h=256, size=170, border=True):
    img = Image.new("RGB", (w, h), BG)
    d = ImageDraw.Draw(img)
    f = font(size)
    box = d.textbbox((0, 0), text, font=f)
    tw, th = box[2] - box[0], box[3] - box[1]
    d.text(((w - tw) / 2 - box[0], (h - th) / 2 - box[1]), text, font=f, fill=GOLD)
    if border:
        d.rectangle([8, 8, w - 9, h - 9], outline=GOLD, width=6)
    img = img.transpose(Image.FLIP_LEFT_RIGHT)   # Blender 平面 UV 反向，预先镜像
    img.save(out)
    print("wrote", out, img.size)


def couplet(text, out, w=160, h=1024, size=96):
    img = Image.new("RGB", (w, h), (240, 236, 226))
    d = ImageDraw.Draw(img)
    f = font(size)
    n = len(text)
    for i, ch in enumerate(text):
        box = d.textbbox((0, 0), ch, font=f)
        tw = box[2] - box[0]
        y = 20 + i * ((h - 40) / n)
        d.text(((w - tw) / 2 - box[0], y), ch, font=f, fill=(58, 42, 28))
    img.save(out)
    print("wrote", out, img.size)


if __name__ == "__main__":
    plaque("鰲台書院", os.path.join(OUT, "plaque_gate.png"))
    plaque("講堂", os.path.join(OUT, "plaque_hall.png"), w=768, h=256, size=160)
    couplet("書聲琅琅傳嶺南", os.path.join(OUT, "couplet_l.png"))
    couplet("文脈綿綿續鰲臺", os.path.join(OUT, "couplet_r.png"))
