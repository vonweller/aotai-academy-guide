# -*- coding: utf-8 -*-
import json, os, time, urllib.parse, urllib.request
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'relics', 'raw'))
UA = 'AotaiEduBot/1.0 (Dongguan Aotai student museum demo; educational)'
def api(params):
    url = 'https://commons.wikimedia.org/w/api.php?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=40) as resp:
        return json.loads(resp.read().decode('utf-8'))
def download(url, path):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=40) as resp:
        data = resp.read()
    if len(data) < 2000:
        return False
    open(path, 'wb').write(data)
    return True
wanted = {
 'xiangyunsha': ['gambiered silk','mud silk fabric','black silk fabric texture','silk gauze black close up','香云纱'],
 'guancao': ['rush basket','straw mat texture','handmade grass basket','basket weaving grass','reed mat weaving'],
 'qianjiaodeng': ['Thousand-Corner Lantern','traditional Chinese red lantern','Chinese palace lantern','red paper lantern close'],
 'other': ['blank white wall indoor','wooden table top empty','human hand close up','office ceiling'],
}
manifest = []
seen = set()
for cls, qs in wanted.items():
    folder = os.path.join(ROOT, cls)
    os.makedirs(folder, exist_ok=True)
    got = 0
    for q in qs:
        if got >= 10:
            break
        try:
            data = api({'action':'query','format':'json','generator':'search','gsrsearch':q,'gsrnamespace':'6','gsrlimit':'10','prop':'imageinfo','iiprop':'url|mime','iiurlwidth':'420'})
        except Exception as e:
            print('search fail', cls, q, e)
            continue
        pages = (data.get('query') or {}).get('pages') or {}
        for p in pages.values():
            if got >= 10:
                break
            info = (p.get('imageinfo') or [{}])[0]
            if info.get('mime') not in ('image/jpeg','image/png','image/webp'):
                continue
            title = p.get('title') or ''
            if 'djvu' in title.lower() or 'map of' in title.lower():
                continue
            url = (info.get('thumburl') or '').split('?')[0]
            if not url or url in seen:
                continue
            seen.add(url)
            ext = '.png' if url.lower().endswith('.png') else '.jpg'
            path = os.path.join(folder, '%02d%s' % (got, ext))
            try:
                ok = download(url, path)
            except Exception as e:
                print('dl fail', e)
                ok = False
            if not ok:
                continue
            manifest.append({'class': cls, 'file': path, 'title': title, 'url': url, 'query': q})
            got += 1
            print('OK', cls, got, title[:60])
        time.sleep(0.15)
    print('CLASS', cls, got)
open(os.path.join(ROOT, 'manifest.json'), 'w', encoding='utf-8').write(json.dumps(manifest, ensure_ascii=False, indent=2))
print('TOTAL', len(manifest))