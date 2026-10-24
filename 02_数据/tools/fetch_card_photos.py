# -*- coding: utf-8 -*-
"""为五候选类别抓取多张自由许可图片（供打印认物卡使用）。"""
import json, os, re, sys, time, urllib.parse, urllib.request
sys.stdout.reconfigure(encoding='utf-8')
UA = 'AotaiEduBot/1.0 (Dongguan Aotai student museum demo; educational)'
API = 'https://commons.wikimedia.org/w/api.php'
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'relics', 'raw'))
OK = ('public domain', 'cc0', 'cc by', 'cc-by', 'cc by-sa', 'cc-by-sa')

QUERIES = {
 'houjie_yuexiu': ['Chinese silk embroidery detail', 'Chinese embroidery panel museum',
                   'silk embroidery flower bird China', 'embroidery Qing dynasty silk'],
 'houjie_shuangshou_hongquan': ['Hung Gar kung fu practice', 'Southern Chinese martial arts',
                                'Chinese martial arts weapons form', 'kung fu stance China'],
 'aotai_aoyu_brick': ['Chinese brick carving relief', 'Chinese architectural carved brick',
                      'brick relief China temple', 'Chinese carved brick panel'],
 'guancao': ['Chinese woven basket museum', 'bamboo weaving China museum',
             'Chinese straw hat weaving', 'woven mat China museum'],
 'qingxi_qilin_zhazuo': ['Chinese lion dance head', 'lion dance costume China',
                         'Chinese paper lantern craft', 'qilin statue China'],
}

def api(p):
    u = API + '?' + urllib.parse.urlencode(p)
    r = urllib.request.Request(u, headers={'User-Agent': UA})
    with urllib.request.urlopen(r, timeout=40) as x:
        return json.loads(x.read().decode())

def fetch(u):
    r = urllib.request.Request(u, headers={'User-Agent': UA})
    with urllib.request.urlopen(r, timeout=50) as x:
        return x.read()

def main():
    os.makedirs(ROOT, exist_ok=True)
    manifest = {}
    mp = os.path.join(ROOT, 'manifest_v2.json')
    if os.path.isfile(mp):
        try: manifest = json.load(open(mp, encoding='utf-8'))
        except Exception: manifest = {}
    for cls, qs in QUERIES.items():
        folder = os.path.join(ROOT, cls)
        os.makedirs(folder, exist_ok=True)
        have = len([f for f in os.listdir(folder) if f.lower().endswith(('.jpg', '.png'))])
        if have >= 4:
            print(cls, 'skip_have', have, flush=True); continue
        got = 0
        seen = set()
        for q in qs:
            if got >= 6: break
            try:
                d = api({'action': 'query', 'format': 'json', 'generator': 'search',
                         'gsrsearch': q, 'gsrnamespace': 6, 'gsrlimit': 20,
                         'prop': 'imageinfo', 'iiprop': 'url|mime|extmetadata', 'iiurlwidth': 1100})
            except Exception as e:
                print('  search fail', q, type(e).__name__, flush=True); time.sleep(3); continue
            for p in ((d.get('query') or {}).get('pages') or {}).values():
                if got >= 6: break
                info = (p.get('imageinfo') or [{}])[0]
                md = info.get('extmetadata') or {}
                lic = ((md.get('LicenseShortName') or {}).get('value') or '').strip()
                if not any(k in lic.lower() for k in OK): continue
                if info.get('mime') not in ('image/jpeg', 'image/png'): continue
                t = p.get('title') or ''
                if any(x in t.lower() for x in ('djvu', '.pdf', 'map', 'postcard', '.svg')): continue
                if t in seen: continue
                seen.add(t)
                url = info.get('thumburl') or info.get('url')
                if not url: continue
                try:
                    data = fetch(url)
                except Exception as e:
                    print('   dl fail', type(e).__name__, flush=True); time.sleep(2); continue
                if len(data) < 20000: continue
                fn = os.path.join(folder, '%02d.jpg' % got)
                open(fn, 'wb').write(data)
                manifest.setdefault(cls, []).append({
                    'file': '%s/%02d.jpg' % (cls, got), 'title': t, 'license': lic,
                    'author': re.sub(r'<[^>]+>', '', ((md.get('Artist') or {}).get('value') or '')).strip()[:120],
                    'source': 'https://commons.wikimedia.org/wiki/' + urllib.parse.quote(t.replace(' ', '_')),
                    'query': q, 'bytes': len(data)})
                got += 1
                print(cls, 'ok', got, lic, t[:56], flush=True)
                time.sleep(1.2)
            time.sleep(1.5)
    json.dump(manifest, open(mp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('DONE classes=', len(manifest))

if __name__ == '__main__':
    main()
