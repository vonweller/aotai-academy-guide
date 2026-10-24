# -*- coding: utf-8 -*-
"""生成 A4 打印卡片（五候选版）：人脸样张 + 五张非遗认物卡 + 来源说明。

版式沿用原认物卡：标题 / 副标题 / 主图 / 次图 / 历史小档案 / 底部来源行。
"""
import io, json, os, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(ROOT, '07_打印卡片', '02_非遗认物卡')
RAW = os.path.join(ROOT, '02_数据', 'relics', 'raw')
DPI = 300
A4 = (int(8.27 * DPI), int(11.69 * DPI))
FB = 'C:/Windows/Fonts/msyhbd.ttc'
FR = 'C:/Windows/Fonts/msyh.ttc'
GOLD = (176, 132, 52)
INK = (45, 40, 34)
GREY = (110, 105, 96)

def font(p, s):
    return ImageFont.truetype(p, s)

def ctext(d, box, text, f, fill):
    x0, y0, x1, y1 = box
    w = d.textlength(text, font=f)
    asc, desc = f.getmetrics()
    d.text(((x0 + x1 - w) / 2, (y0 + y1 - (asc + desc)) / 2), text, font=f, fill=fill)

def load(path, box_w, box_h, centering=(0.5, 0.5)):
    im = ImageOps.exif_transpose(Image.open(path).convert('RGB'))
    return ImageOps.fit(im, (box_w, box_h), Image.LANCZOS, centering=centering)

# 五候选：与 content.json relics 顺序一致
CARDS = [
    ('houjie_yuexiu', '厚街粤绣', '粤绣以针代笔，花鸟鱼虫皆可入绣',
     '粤绣是广府地区传统刺绣，针脚细密、色彩浓艳，常用金银线盘绣。'
     '在东莞一带，刺绣长期是水乡女子的日常手艺。'),
    ('houjie_shuangshou_hongquan', '厚街双手洪拳', '南拳一支，讲桥手与马步',
     '双手洪拳属南拳体系，讲究桥手沉稳、马步生根，出手讲求整劲。'
     '练拳先从扎马与桥手入手，再学套路与器械。'),
    ('aotai_aoyu_brick', '鳌鱼砖', '建筑砖雕，鳌鱼为岭南常见题材',
     '鳌鱼砖是岭南建筑上的砖雕构件，多用于屋脊、墀头与墙面装饰。'
     '鳌鱼取「独占鳌头」之意，寄托读书登科的期望。'),
    ('guancao', '莞草编织', '咸水草压挑成席、成篮、成帽',
     '莞草又称咸水草，多生于东莞河边滩地。晒干压扁后一压一挑，'
     '编成草席、草篮、草帽，是水乡人家最日常的手艺。'),
    ('qingxi_qilin_zhazuo', '清溪麒麟扎作', '竹篾扎骨，糊纸彩绘',
     '麒麟扎作以竹篾扎出骨架，再糊纸、上彩、绘鳞。'
     '清溪一带的麒麟舞所用的麒麟头，正出自这类扎作手艺。'),
]

def make_card(idx, key, title, subtitle, history, main_img, sub_img, credit):
    W, H = A4
    img = Image.new('RGB', (W, H), 'white')
    d = ImageDraw.Draw(img)
    ctext(d, (0, 60, W, 150), title, font(FB, 76), (25, 25, 25))
    ctext(d, (0, 160, W, 220), '非遗认物卡 · 对准镜头，认准后自动讲历史并出题', font(FR, 34), GREY)
    ctext(d, (0, 226, W, 262), subtitle, font(FR, 30), GOLD)

    # 主图
    mw, mh = 1780, 950
    mx = (W - mw) // 2
    my = 300
    if main_img:
        img.paste(load(main_img, mw, mh, (0.5, 0.45)), (mx, my))
    d.rectangle([mx, my, mx + mw, my + mh], outline=(0, 0, 0), width=4)

    # 次图
    sw, sh = 700, 620
    sx = (W - sw) // 2
    sy = my + mh + 90
    if sub_img:
        img.paste(load(sub_img, sw, sh), (sx, sy))
    d.rectangle([sx, sy, sx + sw, sy + sh], outline=(0, 0, 0), width=4)

    # 历史小档案
    ty = sy + sh + 70
    d.text((150, ty), '历史小档案', font=font(FB, 44), fill=INK)
    ty += 72
    line = ''
    for ch in history:
        if d.textlength(line + ch, font=font(FR, 34)) > (W - 300):
            d.text((150, ty), line, font=font(FR, 34), fill=(60, 55, 48))
            ty += 52
            line = ch
        else:
            line += ch
    if line:
        d.text((150, ty), line, font=font(FR, 34), fill=(60, 55, 48))

    d.text((150, H - 80), '图片 %s · 课堂演示用' % credit, font=font(FR, 22), fill=(150, 148, 142))
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, 'A4_%02d_%s.jpg' % (idx, title))
    img.save(p, quality=94, dpi=(DPI, DPI))
    print('saved', os.path.basename(p))
    return p

# 人工目检后选定的主图/次图（避免脚本随意取到不相关照片）
CHOICE = {
    'houjie_yuexiu': ('01.jpg', '04.jpg'),
    'houjie_shuangshou_hongquan': ('p3.jpg', 'p4.jpg'),
    'aotai_aoyu_brick': ('00.jpg', '01.jpg'),
    'guancao': ('03.jpg', '00.jpg'),
    'qingxi_qilin_zhazuo': ('03.jpg', '05.jpg'),
}


def main():
    man = {}
    mp = os.path.join(RAW, 'manifest_v2.json')
    if os.path.isfile(mp):
        try: man = json.load(open(mp, encoding='utf-8'))
        except Exception: man = {}
    used = {}
    for i, (key, title, sub, hist) in enumerate(CARDS, 1):
        folder = os.path.join(RAW, key)
        main_name, sub_name = CHOICE.get(key, (None, None))
        main_img = os.path.join(folder, main_name) if main_name else None
        sub_img = os.path.join(folder, sub_name) if sub_name else None
        if not main_img or not os.path.isfile(main_img):
            print('SKIP missing main image', key); continue
        if sub_img and not os.path.isfile(sub_img):
            sub_img = None
        credit = 'Wikimedia Commons'
        recs = man.get(key) or []
        if recs:
            lic = sorted({r['license'] for r in recs if r.get('license')})
            if lic:
                credit = 'Wikimedia Commons · ' + ' / '.join(lic)
        used[key] = [main_name] + ([sub_name] if sub_img else [])
        make_card(i, key, title, sub, hist, main_img, sub_img, credit)
    json.dump(used, open(os.path.join(OUT, '_used.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

if __name__ == '__main__':
    main()
