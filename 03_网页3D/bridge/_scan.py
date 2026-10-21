import asyncio, os, json

async def main():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.launch(
            executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',
            args=['--no-sandbox'])
        pg = await b.new_page(viewport={'width': 1600, 'height': 900})
        await pg.goto('http://127.0.0.1:8000/', wait_until='domcontentloaded')
        await pg.wait_for_timeout(6000)
        res = await pg.evaluate('''() => {
            const w = window.AOTAI.world;
            const root = w.glbGroup || w.scene;
            const pts = [];
            root.updateMatrixWorld(true);
            root.traverse(o => {
                if (!o.isMesh) return;
                const pos = o.geometry.attributes.position;
                if (!pos) return;
                const V = o.position.constructor;
                const v = new V();
                const step = Math.max(1, Math.floor(pos.count / 8000));
                for (let i = 0; i < pos.count; i += step) {
                    v.fromBufferAttribute(pos, i).applyMatrix4(o.matrixWorld);
                    if (v.y > 0.6) pts.push([+v.x.toFixed(1), +v.y.toFixed(1), +v.z.toFixed(1)]);
                }
            });
            return pts;
        }''')
        print('pts', len(res))
        import collections
        buck = collections.defaultdict(list)
        for x, y, z in res:
            buck[int(z // 2) * 2].append((x, y))
        print('%-12s %6s %14s %10s' % ('z区段', 'n', 'x范围', 'y最高'))
        for k in sorted(buck):
            seg = buck[k]
            if len(seg) < 20: continue
            sx = [p[0] for p in seg]; sy = [p[1] for p in seg]
            print('z %+4d..%+4d %6d  %6.1f..%6.1f  %6.2f' % (k, k+2, len(seg), min(sx), max(sx), max(sy)))
        await b.close()

asyncio.run(main())