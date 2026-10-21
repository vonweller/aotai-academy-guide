# 网页 3D 虚拟交互（鳌台书院 · 五关导览）

## 一键运行（推荐）
```bash
python 03_网页3D/bridge/run_demo.py
```
打开控制台打印的 `http://127.0.0.1:8000/`（投影端用局域网地址）。
它会同时启动：
- **MQTT broker**（tcp 1883，零依赖实现）：CyberCAM / K10 连这个
- **Flask 后端**（:8000）：静态网站 + `/api/*` + SSE + MQTT 桥

## 只跑后端（已有 mosquitto）
```bash
python 03_网页3D/bridge/app.py --port 8000 --mqtt 127.0.0.1:1883
```

## 纯静态（不联网、不启动后端）
双击 `index.html` 也能演示（缺少音频与 MQTT，会退化为浏览器 `speechSynthesis` 朗读）。
强烈建议用后端方式，音质与联动才完整。

## 操作
| 键 | 作用 |
|---|---|
| `N` / `→` | 下一关（小鳌沿路径走过去） |
| `P` / `←` | 上一关 |
| `空格` | 重播本关讲解 |
| `L` | 粤语 / 普通话切换 |
| `R` | 重置到第一关 |
| `C` | 切换机位（总览 / 门口 / 讲堂 / 后园） |
| `V` | 语音开关 |
| `1`–`5` | 直接跳到某关 |
| 鼠标拖拽 / 滚轮 | 旋转、缩放视角 |

## 关联动线
1. **门口迎宾**：人脸识别（CyberCAM 上报 `face_recognized`，或点「模拟识别」）
2. **前院溯源**：书院历史 + 问答 1
3. **讲堂楹联**：楹联领读
4. **非遗工坊**：香云纱 / 莞草编织 + 问答 2
5. **尾声留墨**：结语与参观路线

## 文件
```
index.html                 页面骨架
assets/css/style.css       主题样式（水墨/金/黛瓦）
assets/js/scene.js         Three.js 场景（程序化岭南书院 + 小人 + 跟随镜头）
assets/js/app.js           五关状态机、语音、按钮、键盘、SSE/MQTT 联动
assets/map.json            关卡坐标与行走路径（与 02_数据/map.json 同步）
assets/aotai_academy.glb   Blender 产出的场景（存在则优先加载）
assets/vendor/three/       Three.js 本地副本（断网可用）
bridge/app.py              Flask 后端 + MQTT 桥 + SSE
bridge/broker.py           零依赖 MQTT broker（内网演示）
bridge/run_demo.py         一键启动
qc/                        Playwright 自动截图（验收用）
```

## 与硬件联动
- CyberCAM / K10 都把事件发到 `aotai/event`、`aotai/k10`，网页通过 SSE 即时更新；
- 网页按钮把 `aotai/web` / `aotai/cmd` 发回去，CyberCAM 收到后切关/播报；
- MQTT 主题见 `../../06_文档/协议.md`。
