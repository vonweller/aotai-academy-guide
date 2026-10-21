@echo off
chcp 65001 >nul
title 鳌台书院 AI 非遗导览
echo ============================================================
echo   鳌台书院 AI 非遗导览 - 一键演示
echo   1) 启动 MQTT Broker (1883) + Flask 网页 (8000)
echo   2) 浏览器打开 http://127.0.0.1:8000/
echo ============================================================
cd /d "%~dp0"
python 03_网页3D\bridge\run_demo.py --port 8000 --mqtt-port 1883
pause
