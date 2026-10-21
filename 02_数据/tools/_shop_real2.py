import io, json, os, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from PIL import Image, ImageDraw, ImageFont, ImageOps
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(ROOT, '07_打印卡片', '04_兑换立牌')
SRC = os.path.join(ROOT, '02_数据', 'prizes_src')
DPI = 300
A4 = (int(8.27*DPI), int(11.69*DPI))
FB = 'C:/Windows/Fonts/msyhbd.ttc'
FR = 'C:/Windows/Fonts/msyh.ttc'
def font(p,s): return ImageFont.truetype(p,s)
def ctext(d, box, text, f, fill):
    x0,y0,x1,y1 = box
    w = d.textlength(text, font=f)
    asc, desc = f.getmetrics()
    d.text(((x0+x1-w)/2, (y0+y1-(asc+desc))/2), text, font=f, fill=fill)
GOLD=(176,132,52); DARK=(32,30,28); CREAM=(250,246,238); INK=(45,40,34)
def thumb(path, size):
    im = ImageOps.exif_transpose(Image.open(path).convert('RGB'))
    im = ImageOps.fit(im, (size,size), Image.LANCZOS, centering=(0.5,0.42))
    mask = Image.new('L', (size,size), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0,0,size,size], radius=int(size*0.16), fill=255)
    out = Image.new('RGB', (size,size), (255,253,248))
    out.paste(im, (0,0), mask)
    return out
# 每件奖品：真实物品照片
ITEMS = [
  ('pin_30.jpg', '香云纱徽章', 30, '珐琅徽章'),
  ('bookmark_51.jpg', '莞草纹书签', 45, '实物书签'),
  ('tassel_16.jpg', '千角灯流苏挂饰', 60, '中式流苏佩饰'),
  ('figure_15.jpg', '非遗彩绘手办', 90, '彩绘瓷偶'),
  ('figure_11.jpg', '书院人物手办', 120, '彩绘瓷偶'),
]
img = Image.new('RGB', A4, CREAM)
d = ImageDraw.Draw(img)
W,H = A4
head_h = int(H*0.150)
d.rectangle([0,0,W,head_h], fill=DARK)
d.rectangle([0,head_h-16,W,head_h], fill=GOLD)
ctext(d,(0,int(H*0.024),W,int(H*0.092)),'非遗护照 · 积分兑换',font(FB,90),(234,208,152))
ctext(d,(0,int(H*0.090),W,head_h-24),'答对题目 · 认出文物 · 走完五关，都能攒积分',font(FR,33),(198,188,168))
L=130; R=W-130
y=int(H*0.178)
d.text((L,y),'积分怎么攒',font=font(FB,46),fill=(120,86,26))
y+=70
rules=[('人脸识别通过','+10'),('每关答对一题','+15'),('火眼金睛认出一件','+8'),
       ('火眼金睛再答对','+20'),('五关全部走完','+50')]
colw=(R-L)//2
for i,(txt,val) in enumerate(rules):
    rw,cc=divmod(i,2)
    x=L+cc*(colw+36)
    yy=y+rw*56
    d.text((x,yy),txt,font=font(FR,30),fill=(70,62,52))
    vw=d.textlength(val,font=font(FB,31))
    d.text((x+colw-104-vw,yy),val,font=font(FB,31),fill=(150,60,40))
y+=56*3+24
d.line([(L,y),(R,y)],fill=(212,200,180),width=4)
y+=38
d.text((L,y),'可以换什么',font=font(FB,46),fill=(120,86,26))
tip='（奖品实物以现场为准，图为同类参考）'
d.text((L+d.textlength('可以换什么',font=font(FB,46))+24, y+16), tip, font=font(FR,24), fill=(150,140,124))
y+=70
gap=14
card_h=(H-112-y-30-gap*4)//5
th=int(card_h*0.80)
for fname, name, cost, kind in ITEMS:
    d.rounded_rectangle([L,y,R,y+card_h], radius=20, fill=(255,253,248),
                        outline=(220,210,192), width=3)
    im = thumb(os.path.join(SRC,fname), th)
    ix = L + int(card_h*0.16)
    iy = y + (card_h-th)//2
    img.paste(im, (ix,iy))
    d.rounded_rectangle([ix,iy,ix+th,iy+th], radius=int(th*0.16), outline=(222,212,194), width=2)
    tx = ix + th + int(card_h*0.26)
    d.text((tx, y+card_h//2-int(card_h*0.30)), name, font=font(FB,38), fill=INK)
    d.text((tx, y+card_h//2+int(card_h*0.06)), kind, font=font(FR,25), fill=(150,140,124))
    cost_txt=str(cost)
    cw=d.textlength(cost_txt,font=font(FB,48))
    d.text((R-146-cw, y+card_h//2-int(card_h*0.30)), cost_txt, font=font(FB,48), fill=(150,60,40))
    d.text((R-132, y+card_h//2-int(card_h*0.10)), '分', font=font(FR,27), fill=(140,130,116))
    y+=card_h+gap
d.rectangle([0,H-112,W,H],fill=DARK)
ctext(d,(0,H-110,W,H-2),'网页右上角点「🎁 积分」查看与兑换 · 兑换后到工作人员处领取',font(FR,29),fill=(228,216,192))
os.makedirs(OUT,exist_ok=True)
p=os.path.join(OUT,'A4_积分兑换立牌.jpg')
img.save(p,quality=96,dpi=(DPI,DPI))
print('saved',p)