@echo off
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion
title 鳌台书院 AI 非遗导览 - 一键启动
cd /d "%~dp0"

echo ============================================================
echo    鳌台书院 AI 非遗导览
echo    CyberCAM + 网页3D + 语音导览
echo ============================================================
echo.

set "PY="
set "PIP="
set "ERR=0"

REM ---------- 1. 找 Python ----------
echo [1/6] 检查 Python ...
where python >nul 2>&1
if not errorlevel 1 (
    set "PY=python"
) else (
    where py >nul 2>&1
    if not errorlevel 1 set "PY=py -3"
)
if "!PY!"=="" (
    echo    [X] 没找到 Python。
    echo        请到 https://www.python.org/downloads/ 下载安装，
    echo        安装时务必勾选 Add Python to PATH，然后重新运行本脚本。
    set "ERR=1"
    goto :fail
)
for /f "delims=" %%v in ('!PY! -V 2^>^&1') do set "PYVER=%%v"
echo    [OK] !PYVER!

REM ---------- 2. Python 依赖 ----------
echo [2/6] 检查 Python 依赖 ...
!PY! -c "import flask, paho.mqtt.client" >nul 2>&1
if errorlevel 1 (
    echo    缺少 flask / paho-mqtt，正在安装 ...
    !PY! -m pip install --disable-pip-version-check -q flask paho-mqtt
    if errorlevel 1 (
        echo    [!] 安装失败，尝试国内镜像 ...
        !PY! -m pip install --disable-pip-version-check -q -i https://pypi.tuna.tsinghua.edu.cn/simple flask paho-mqtt
    )
    !PY! -c "import flask, paho.mqtt.client" >nul 2>&1
    if errorlevel 1 (
        echo    [X] Python 依赖安装失败，请检查网络后重试。
        set "ERR=1"
        goto :fail
    )
)
echo    [OK] flask + paho-mqtt

REM ---------- 3. 端口检查 ----------
echo [3/6] 检查端口 8000 ...
set "BUSY="
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8000" ^| findstr LISTENING') do set "BUSY=%%p"
if not "!BUSY!"=="" (
    echo    [!] 端口 8000 被占用 ^(PID !BUSY!^)，可能是上次没关干净。
    echo        正在结束该进程 ...
    taskkill /PID !BUSY! /F >nul 2>&1
    timeout /t 2 >nul
)
echo    [OK] 端口可用

REM ---------- 4. 数据完整性 ----------
echo [4/6] 检查数据文件 ...
set "DATAOK=1"
if not exist "02_数据\content.json" set "DATAOK=0"
if not exist "03_网页3D\index.html" set "DATAOK=0"
if not exist "03_网页3D\bridge\run_demo.py" set "DATAOK=0"
if not exist "02_数据\audio\zh" set "DATAOK=0"
if "!DATAOK!"=="0" (
    echo    [X] 数据文件不完整，请确认本脚本和 02_数据 / 03_网页3D 在同一目录。
    set "ERR=1"
    goto :fail
)
for /f %%c in ('dir /b "02_数据\audio\zh\*.mp3" 2^>nul ^| find /c /v ""') do set "NAUD=%%c"
echo    [OK] 文案与音频就绪 ^(普通话 !NAUD! 条^)

REM ---------- 5. 可选：CyberCAM ----------
echo [5/6] 检查 CyberCAM 相机 ...
ping -n 1 -w 800 192.168.10.62 >nul 2>&1
if errorlevel 1 (
    echo    [i] 未检测到 CyberCAM ^(192.168.10.62^)，仅启动网页演示。
    echo        需要摄像头联动时，请让相机连同一 WiFi 后重开本脚本。
) else (
    echo    [OK] CyberCAM 在线
)

REM ---------- 6. 启动 ----------
echo [6/6] 启动服务 ...
echo.
echo ============================================================
echo    网页地址: http://127.0.0.1:8000/
echo    关闭本窗口即停止服务
echo ============================================================
echo.
REM 等 Flask 起来再打开浏览器（直接 start 会抢在服务前，出现连接失败）
start "" /min cmd /c "timeout /t 3 >nul & start http://127.0.0.1:8000/"
!PY! "03_网页3D\bridge\run_demo.py" --port 8000
goto :eof

:fail
echo.
echo 启动失败，请按上面的提示处理后重试。
pause
exit /b 1
