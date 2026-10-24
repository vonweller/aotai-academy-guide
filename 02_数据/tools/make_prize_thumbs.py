# -*- coding: utf-8 -*-
"""为新的兑换品生成缩略图（复用对应非遗图片，做成徽章/书签/挂饰样式）。"""
import os, sys
from PIL import Image, ImageDraw, ImageOps
sys.stdout.reconfigure(encoding='utf-8')
ROOT=r'C:\Users\52953\Desktop\智能博物一一粤地非遗物语之东莞熬台书院'
SRC=os.path.join(ROOT,'03_网页3D','assets','relics')
OUT=os.path.join(ROOT,'03_网页3D','assets','prizes')
os.makedirs(OUT,exist_ok=True)

MAP={
 'pin_yuexiu':('houjie_yuexiu', 'badge'),
 'pin_guancao':('guancao', 'bookmark'),
 'pin_qilin':('qingxi_qilin_zhazuo', 'charm'),
 'pin_hongquan':('houjie_shuangshou_hongquan', 'badge'),
 'pin_aoyu':('aotai_aoyu_brick', 'figure'),
}
SIZE=640
GOLD=(201,162,74)
def rounded(im, radius_ratio=0.18):
    w,h=im.size; r=int(min(w,h)*radius_ratio)
    mask=Image.new('L',(w,h),0)
    ImageDraw.Draw(mask).rounded_rectangle([0,0,w-1,h-1],radius=r,fill=255)
    out=Image.new('RGB',(w,h),(18,17,15)); out.paste(im,(0,0),mask); return out

for pid,(src,kind) in MAP.items():
    sp=os.path.join(SRC,src+'.jpg')
    if not os.path.isfile(sp):
        print('MISSING src', src); continue
    im=ImageOps.exif_transpose(Image.open(sp).convert('RGB'))
    canvas=Image.new('RGB',(SIZE,SIZE),(24,23,21))
    d=ImageDraw.Draw(canvas)
    if kind=='badge':
        # 圆形徽章
        im2=ImageOps.fit(im,(int(SIZE*0.72),int(SIZE*0.72)),Image.LANCZOS)
        mask=Image.new('L',im2.size,0)
        ImageDraw.Draw(mask).ellipse([0,0,im2.size[0]-1,im2.size[1]-1],fill=255)
        off=((SIZE-im2.size[0])//2,(SIZE-im2.size[1])//2)
        d.ellipse([off[0]-10,off[1]-10,off[0]+im2.size[0]+10,off[1]+im2.size[1]+10],
                  outline=GOLD,width=8)
        canvas.paste(im2,off,mask)
    elif kind=='bookmark':
        w=int(SIZE*0.52); h=int(SIZE*0.84)
        im2=ImageOps.fit(im,(w,h),Image.LANCZOS)
        off=((SIZE-w)//2,(SIZE-h)//2)
        d.rounded_rectangle([off[0]-8,off[1]-8,off[0]+w+8,off[1]+h+8],radius=10,outline=GOLD,width=6)
        canvas.paste(rounded(im2,0.03),off)
        d.ellipse([SIZE//2-9,off[1]-34,SIZE//2+9,off[1]-16],fill=GOLD)
    elif kind=='charm':
        im2=ImageOps.fit(im,(int(SIZE*0.74),int(SIZE*0.74)),Image.LANCZOS)
        off=((SIZE-im2.size[0])//2,(SIZE-im2.size[1])//2)
        d.rounded_rectangle([off[0]-9,off[1]-9,off[0]+im2.size[0]+9,off[1]+im2.size[1]+9],
                            radius=int(SIZE*0.10),outline=GOLD,width=8)
        canvas.paste(rounded(im2,0.08),off)
        d.line([(SIZE//2,off[1]-9),(SIZE//2,off[1]-52)],fill=GOLD,width=6)
        d.ellipse([SIZE//2-13,off[1]-72,SIZE//2+13,off[1]-46],outline=GOLD,width=6)
    else:  # figure / 摆件
        w=int(SIZE*0.80); h=int(SIZE*0.66)
        im2=ImageOps.fit(im,(w,h),Image.LANCZOS)
        off=((SIZE-w)//2,int(SIZE*0.16))
        d.rounded_rectangle([off[0]-9,off[1]-9,off[0]+w+9,off[1]+h+9],radius=12,outline=GOLD,width=7)
        canvas.paste(rounded(im2,0.05),off)
        base_y=off[1]+h+18
        d.rounded_rectangle([int(SIZE*0.26),base_y,int(SIZE*0.74),base_y+46],radius=8,fill=(58,50,38))
        d.rounded_rectangle([int(SIZE*0.26),base_y,int(SIZE*0.74),base_y+46],radius=8,outline=GOLD,width=3)
    p=os.path.join(OUT,pid+'.jpg')
    canvas.save(p,quality=92)
    print('saved',pid,os.path.getsize(p))
