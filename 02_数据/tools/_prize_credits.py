import io, json, os, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
cands = json.load(open(os.path.join(ROOT,'02_数据','tools','_prize_candidates.json'), encoding='utf-8'))
want = ['pin_30.jpg','bookmark_51.jpg','tassel_16.jpg','figure_15.jpg','figure_11.jpg']
by = {os.path.basename(c['file']): c for c in cands if c.get('file')}
lines = ['# 兑换立牌奖品图片来源', '',
         '立牌用图为同类实物参考照片，正式奖品以现场实物为准。', '']
for w in want:
    c = by.get(w)
    if not c:
        lines.append('- ' + w + '：（缺）'); continue
    lines.append('## ' + c['title'].replace('File:',''))
    lines.append('- 许可：' + c['lic'])
    lines.append('- 文件：' + c['url'])
    lines.append('')
p = os.path.join(ROOT,'07_打印卡片','03_来源与授权','奖品图片来源.md')
open(p,'w',encoding='utf-8').write('\n'.join(lines))
print('saved', p)
# 清理临时脚本与拼图
for f in ['_find_prizes.py','_find_prizes2.py','_find_prizes3.py','_find_prizes4.py',
          '_find_cats.py','_dl_prizes.py','_dl_prizes2.py','_prize_sheet.py','_picked.py',
          '_shop_sign.py','_shop_sign2.py','_shop_sign3.py','_shop_real.py','_prize_sheet.jpg']:
    fp = os.path.join(ROOT,'02_数据','tools',f)
    if os.path.exists(fp):
        os.remove(fp)
        print('rm', f)