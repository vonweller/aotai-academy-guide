import asyncio, os, json

# 用俯视全貌 + 材质坐标 + 已见过的好画面，最终确定五关机位
# 已知好画面：
#   俯视全景: cam(0, 90, -16) look(0,0,-16) -> 全场景
#   讲堂正面: cam(0, 6, -14) look(0, 3, -20) 附近看到讲堂
#   门楼:     cam(0, 5, -44) look(0,3.5,-31)
CANDS = {
  1: ((-6.0, 5.0, -42.0), (0.0, 3.5, -31.0), '门楼正面斜角'),
  2: ((0.0, 5.0, -34.0), (-1.0, 2.2, -25.0), '前院'),
  3: ((2.0, 6.0, -16.0), (0.0, 3.0, -22.0), '讲堂'),
  4: ((-10.6, 4.0, 4.0), (-10.6, 1.6, -8.0), '工坊正面'),
  5: ((-4.0, 5.0, -10.0), (-9.0, 1.6, -22.0), '六角亭'),
}

async def main():
    from playwright.async_api import async_playwright
    OUT = os.path.abspath('03_网页3D/qc')
    async with async_playwright() as p:
        b = await p.chromium.launch(
            executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',
            args=['--no-sandbox'])
        pg = await b.new_page(viewport={'width': 1600, 'height': 900})
        await pg.goto('http://127.0.0.1:8000/', wait_until='domcontentloaded')
        await pg.wait_for_timeout(6000)
        await pg.click('#startBtn')
        await pg.wait_for_timeout(2500)
        final = {}
        for n in (1,2,3,4,5):
            (cx,cy,cz),(tx,ty,tz),note = CANDS[n]
            await pg.evaluate('''([cx,cy,cz,tx,ty,tz]) => {
                const w = window.AOTAI.world;
                if (w.orbit) w.orbit.enabled = false;
                w.followActor(null);
                w.camera.up.set(0,1,0);
                w.camera.position.set(cx,cy,cz);
                w.camera.lookAt(tx,ty,tz);
                w.renderer.render(w.scene, w.camera);
            }''', [cx,cy,cz,tx,ty,tz])
            await pg.wait_for_timeout(320)
            await pg.screenshot(path=os.path.join(OUT, 'final_s%d.png' % n))
            final[n] = {'from': list((cx,cy,cz)), 'look': list((tx,ty,tz))}
            print('s%d %s' % (n, note))
        json.dump(final, open(os.path.join(OUT,'final_cams.json'),'w'), indent=1)
        await b.close()

asyncio.run(main())