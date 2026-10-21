# CyberCAM · 鳌台书院 AI 导览 APP

## 部署
1. 文件夹改名为 `aotai`，整个拷到板子 `/data/app/aotai/`
2. `02_数据/` 拷成板子 `/data/aotai/`（content.json、audio/、faces/）
3. 改 `config.py` 里 `MQTT_HOST` 为电脑 IP
4. 运行：`cd /data/app/aotai && python main.py`（或桌面点「鳌台书院AI导览」图标）

## 模块
| 文件 | 作用 |
|---|---|
| main.py | 五关状态机、按键/触摸/MQTT 分发 |
| ui.py | 640×480 自绘界面（中文用文泉驿，PC 上自动退 Pillow） |
| face.py | KPU FACE_DETECT 检测 + OpenCV LBPH 识别 + 现场注册 |
| audio.py | 本地 mp3 优先播放，缺失时在线 TTS 合成并缓存 |
| bus.py | paho-mqtt 封装，断网自动降级 |
| touch.py | /dev/input/event0 裸解析 + 三点标定 |
| content_loader.py | content.json 读取与回退 |
| config.py | 网络、路径、阈值、关卡名 |

## 按键
| 键 | 作用 |
|---|---|
| K（板载） | 语言页确认 / 人脸页注册当前人脸 / 关卡页下一关 |
| 键盘 1 / 2 | 普通话 / 粤语 |
| N / P / R / L | 下一关 / 上一关 / 重播 / 切语言 |
| S | 模拟人脸识别成功（演示） |

## 自检
```bash
python tools/selftest_ui.py     # 生成全部界面 PNG 到 qc/
python tools/prepare_face.py --out ../../02_数据/data_pack   # 人脸样张
python tools/make_icon.py --out .                             # 图标
```
