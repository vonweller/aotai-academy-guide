# -*- coding: utf-8 -*-
import asyncio, json, os, time
import paho.mqtt.client as mqtt
from playwright.async_api import async_playwright

OUT = r"C:\Users\52953\Desktop\智能博物一一粤地非遗物语之东莞熬台书院\03_网页3D\qc"

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True,
            executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            args=["--disable-gpu","--no-sandbox","--autoplay-policy=no-user-gesture-required","--hide-scrollbars"])
        page = await b.new_page(viewport={"width":1600,"height":900})
        logs = []
        page.on("pageerror", lambda e: logs.append("ERR " + str(e)))
        await page.goto("http://127.0.0.1:8000/", wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_function("() => window.AOTAI && window.AOTAI.world && window.AOTAI.world.glbLoaded", timeout=90000)
        await page.wait_for_timeout(1500)
        # 看设备状态 chip
        chip = await page.evaluate("() => document.querySelector('#chipNet') ? document.querySelector('#chipNet').textContent : ''")
        print("CHIP:", chip)
        await page.screenshot(path=os.path.join(OUT, "00_online.png"))
        await b.close()

    # 通过 MQTT 模拟 K10 说「下一关」，看网页是否响应（另开浏览器）
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True,
            executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            args=["--disable-gpu","--no-sandbox","--hide-scrollbars"])
        page = await b.new_page(viewport={"width":1600,"height":900})
        await page.goto("http://127.0.0.1:8000/", wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_function("() => window.AOTAI && window.AOTAI.world && window.AOTAI.world.glbLoaded", timeout=90000)
        await page.evaluate("() => document.querySelector('#startBtn').click()")
        await page.wait_for_timeout(3000)

        # 发 K10 语音指令
        c = mqtt.Client(client_id="k10-sim-%d" % int(time.time()))
        c.username_pw_set("siot", "dfrobot")
        c.connect("159.75.137.223", 1883, 30)
        c.loop_start()
        time.sleep(0.6)
        c.publish("aotai/k10", json.dumps({"type": "voice_cmd", "cmd": "next", "text": "下一关",
                                           "lang": "zh", "stage": 1, "source": "k10-01"}, ensure_ascii=False))
        time.sleep(3.0)
        st = await page.evaluate("() => ({stage: window.AOTAI.state.stage, walking: window.AOTAI.state.walking})")
        print("AFTER K10 'next':", json.dumps(st, ensure_ascii=False))
        c.publish("aotai/k10", json.dumps({"type": "voice_cmd", "cmd": "lang_yue", "text": "粤语",
                                           "lang": "zh", "stage": 2, "source": "k10-01"}, ensure_ascii=False))
        time.sleep(2.5)
        st2 = await page.evaluate("() => ({lang: window.AOTAI.state.lang})")
        print("AFTER K10 'yue':", json.dumps(st2, ensure_ascii=False))
        # 等走完
        await page.wait_for_timeout(9000)
        await page.screenshot(path=os.path.join(OUT, "00_k10_driven.png"))
        c.loop_stop(); c.disconnect()
        print("LOGS", logs[:3])
        await b.close()

asyncio.run(main())
