# -*- coding: utf-8 -*-
"""从 Wikimedia Commons 抓取五候选类别的自由许可图片，并记录出处与授权。

只接受 Public domain / CC0 / CC BY / CC BY-SA 等可再分发许可；
抓不到合规图片就返回 None，调用方应显示占位而不是编造。
"""
import json, os, sys, time, urllib.parse, urllib.request

UA = 'AotaiEduBot/1.0 (Dongguan Aotai student museum demo; educational)'
OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..',
                                   '03_网页3D', 'assets', 'relics'))
RAW = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'relics', 'candidates'))
API = 'https://commons.wikimedia.org/w/api.php'

QUERIES = {
    'houjie_yuexiu': ['Cantonese embroidery', 'Guangdong embroidery silk', 'Chinese silk embroidery panel'],
    'houjie_shuangshou_hongquan': ['Chinese martial arts stance', 'Hung Gar kung fu', 'Chinese martial arts pose'],
    'aotai_aoyu_brick': ['Chinese brick carving', 'Chinese architectural brick relief', 'Cantonese brick ornament'],
    'guancao': ['straw mat weaving', 'rush weaving craft', 'grass mat handmade'],
    'qingxi_qilin_zhazuo': ['Chinese qilin dance costume', 'Chinese lion dance head', 'qilin lantern'],
}
OK_LICENSES = ('public domain', 'cc0', 'cc by', 'cc-by', 'cc by-sa', 'cc-by-sa')

def api(params):
    url = API + '?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read().decode('utf-8'))

def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read()

def pick(cls):
    for q in QUERIES[cls]:
        try:
            d = api({'action': 'query', 'format': 'json', 'generator': 'search',
                     'gsrsearch': q, 'gsrnamespace': 6, 'gsrlimit': 15,
                     'prop': 'imageinfo', 'iiprop': 'url|mime|extmetadata',
                     'iiurlwidth': 900})
        except Exception as e:
            print('  search fail', q, e, flush=True)
            continue
        pages = (d.get('query') or {}).get('pages') or {}
        for p in pages.values():
            info = (p.get('imageinfo') or [{}])[0]
            if info.get('mime') not in ('image/jpeg', 'image/png', 'image/webp'):
                continue
            md = info.get('extmetadata') or {}
            lic = ((md.get('LicenseShortName') or {}).get('value') or '').strip()
            if not any(k in lic.lower() for k in OK_LICENSES):
                continue
            title = p.get('title') or ''
            if 'djvu' in title.lower() or '.pdf' in title.lower() or 'map' in title.lower():
                continue
            url = info.get('thumburl') or info.get('url')
            if not url:
                continue
            try:
                data = fetch(url)
            except Exception as e:
                print('  dl fail', e, flush=True)
                continue
            if len(data) < 8000:
                continue
            author = ((md.get('Artist') or {}).get('value') or '').strip()
            if '<' in author:
                import re
                author = re.sub(r'<[^>]+>', '', author)
            author = ' '.join(author.split())[:120]
            return {
                'cls': cls, 'bytes': data, 'query': q, 'title': title,
                'desc_url': 'https://commons.wikimedia.org/wiki/' + urllib.parse.quote(title.replace(' ', '_')),
                'license': lic, 'author': author,
            }
    return None

def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(RAW, exist_ok=True)
    manifest = {}
    mpath = os.path.join(OUT, 'credits.json')
    if os.path.exists(mpath):
        try:
            manifest = json.load(open(mpath, encoding='utf-8'))
        except Exception:
            manifest = {}
    for cls in QUERIES:
        got = pick(cls)
        if not got:
            print(cls, 'NO_COMPLIANT_IMAGE', flush=True)
            manifest.pop(cls, None)
            continue
        jpg = os.path.join(OUT, cls + '.jpg')
        open(jpg, 'wb').write(got['bytes'])
        open(os.path.join(RAW, cls + '.jpg'), 'wb').write(got['bytes'])
        manifest[cls] = {
            'title': got['title'], 'license': got['license'], 'author': got['author'],
            'source': got['desc_url'], 'query': got['query'], 'bytes': len(got['bytes']),
        }
        print(cls, 'OK', len(got['bytes']), got['license'], flush=True)
        time.sleep(1.0)
    json.dump(manifest, open(mpath, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('DONE', len(manifest))

if __name__ == '__main__':
    main()
