import io, json, sys, time, urllib.parse, urllib.request
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
UA = 'AotaiEduBot/1.0 (student museum demo; educational)'
def api(p):
    u = 'https://commons.wikimedia.org/w/api.php?' + urllib.parse.urlencode(p)
    rq = urllib.request.Request(u, headers={'User-Agent': UA})
    for k in range(3):
        try:
            with urllib.request.urlopen(rq, timeout=40) as r:
                return json.loads(r.read().decode('utf-8'))
        except Exception:
            if k == 2: raise
            time.sleep(3*(k+1))
Q = [
  ('academy', 'Chinese academy traditional courtyard'),
  ('academy2', 'Lingnan architecture courtyard'),
  ('courtyard', 'Chinese courtyard stone pavement'),
  ('gate', 'Chinese traditional gateway paifang'),
  ('hall', 'Chinese hall interior beams pillars'),
  ('workshop', 'traditional Chinese craft workshop interior'),
  ('loom', 'weaving loom traditional'),
  ('dye', 'indigo dye vats workshop'),
  ('bamboo', 'bamboo weaving craft'),
  ('stone', 'Chinese stone carving decoration'),
]
out = []
for tag, q in Q:
    time.sleep(2.0)
    try:
        d = api({'action':'query','format':'json','generator':'search','gsrsearch':q,
                 'gsrnamespace':'6','gsrlimit':'8','prop':'imageinfo',
                 'iiprop':'url|mime|extmetadata','iiurlwidth':'600'})
    except Exception as e:
        print(tag, 'ERR', str(e)[:40]); continue
    n = 0
    for p in (d.get('query') or {}).get('pages', {}).values():
        info = (p.get('imageinfo') or [{}])[0]
        if info.get('mime') not in ('image/jpeg','image/png'): continue
        t = p.get('title','')
        if any(k in t.lower() for k in ('djvu','map','logo','nazi')): continue
        url = (info.get('thumburl') or '').split('?')[0]
        if not url: continue
        out.append({'tag': tag, 'title': t, 'url': url})
        n += 1
    print(tag, 'new', n)
json.dump(out, open('02_数据/tools/_ref_candidates.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)
print('TOTAL', len(out))