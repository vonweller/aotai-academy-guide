import io, json, os, sys, time, urllib.request
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
UA = 'AotaiEduBot/1.0 (student museum demo; educational)'
cands = json.load(open('02_数据/tools/_ref_candidates.json', encoding='utf-8'))
OUT = '02_数据/refs_src'
os.makedirs(OUT, exist_ok=True)
ok = 0
for i, c in enumerate(cands):
    ext = '.png' if c['url'].lower().split('?')[0].endswith('.png') else '.jpg'
    dst = os.path.join(OUT, '%s_%02d%s' % (c['tag'], i, ext))
    if os.path.exists(dst):
        c['file'] = dst; ok += 1; continue
    try:
        req = urllib.request.Request(c['url'], headers={'User-Agent': UA})
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
        if len(data) < 3000: continue
        open(dst,'wb').write(data)
        c['file'] = dst; ok += 1
    except Exception as e:
        print('fail', c['title'][:26], str(e)[:30])
    time.sleep(1.0)
json.dump(cands, open('02_数据/tools/_ref_candidates.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)
print('downloaded', ok)