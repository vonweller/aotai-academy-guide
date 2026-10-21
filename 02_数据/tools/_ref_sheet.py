import glob, os
import cv2, numpy as np
files = sorted(glob.glob('02_数据/refs_src/*.jpg'))
tiles = []
for f in files:
    im = cv2.imdecode(np.fromfile(f, dtype=np.uint8), cv2.IMREAD_COLOR)
    if im is None: continue
    im = cv2.resize(im, (260, 200))
    cv2.rectangle(im, (0,0), (260,24), (0,0,0), -1)
    cv2.putText(im, os.path.basename(f)[:28], (3,17), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255,255,255), 1, cv2.LINE_AA)
    tiles.append(im)
cols = 5
rows = (len(tiles)+cols-1)//cols
sheet = np.zeros((rows*200, cols*260, 3), np.uint8)
for i, t in enumerate(tiles):
    r, c = divmod(i, cols)
    sheet[r*200:(r+1)*200, c*260:(c+1)*260] = t
cv2.imencode('.jpg', sheet)[1].tofile('02_数据/tools/_ref_sheet.jpg')
print('tiles', len(tiles), sheet.shape)