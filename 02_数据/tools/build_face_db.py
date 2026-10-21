import json, os, shutil
import cv2, numpy as np
SRC = os.path.join('02_数据','faces_src','visitor_01.jpg')
OUT = os.path.join('02_数据','data_pack','faces')
img = cv2.imdecode(np.fromfile(SRC, dtype=np.uint8), cv2.IMREAD_COLOR)
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
casc = cv2.CascadeClassifier(os.path.join(cv2.data.haarcascades,'haarcascade_frontalface_default.xml'))
boxes = casc.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=6, minSize=(50,50))
x,y,w,h = max(boxes, key=lambda b: b[2]*b[3])
pad = int(w*0.16)
x0,y0 = max(0,x-pad), max(0,y-pad)
x1,y1 = min(img.shape[1], x+w+pad), min(img.shape[0], y+h+int(pad*1.6))
face = cv2.cvtColor(img[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY)
if os.path.isdir(OUT): shutil.rmtree(OUT)
os.makedirs(OUT)
def prep(g, zoom=1.0, rot=0.0, dx=0, dy=0, bright=0, blur=0, gamma=1.0):
    im = g.astype(np.float32)
    im = (np.power(np.clip(im,0,255)/255.0, gamma)*255.0)
    im = np.clip(im + bright, 0, 255).astype(np.uint8)
    h, w = im.shape
    M = cv2.getRotationMatrix2D((w/2, h/2), rot, zoom)
    M[0,2] += dx; M[1,2] += dy
    im = cv2.warpAffine(im, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
    if blur:
        k = blur*2+1
        im = cv2.GaussianBlur(im, (k,k), 0)
    im = cv2.resize(im, (200,200))
    return cv2.equalizeHist(im)
variants = [
    dict(),
    dict(zoom=1.10),
    dict(zoom=0.92),
    dict(rot=6),
    dict(rot=-6),
    dict(dx=10, dy=6),
    dict(bright=14, gamma=0.9),
    dict(bright=-12, gamma=1.15, blur=1),
]
n = 0
for v in variants:
    n += 1
    out = prep(face, **v)
    cv2.imencode('.jpg', out)[1].tofile(os.path.join(OUT, '1_%02d.jpg' % n))
json.dump({'1':'预约访客'}, open(os.path.join(OUT,'labels.json'),'w',encoding='utf-8'), ensure_ascii=False, indent=2)
base = prep(face)
cv2.imencode('.jpg', base)[1].tofile(os.path.join('02_数据','data_pack','faces','print_visitor.jpg'))
print('samples', n)
files = sorted(f for f in os.listdir(OUT) if f.startswith('1_'))
ims = [cv2.imdecode(np.fromfile(os.path.join(OUT,f), dtype=np.uint8), cv2.IMREAD_GRAYSCALE) for f in files]
mx = 0
for i in range(len(ims)):
    for j in range(i+1, len(ims)):
        d = float(np.mean(np.abs(ims[i].astype(np.float32)-ims[j].astype(np.float32))))
        mx = max(mx, d)
print('max pairwise diff', round(mx,2))