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

## 真实照片展板（`assets/photos/`）
每关场景里立一块**实景照片展板**，让观众看到「这里真实长什么样」。
展板用 billboard（每帧朝相机），任何机位都能读清。

| 关卡 | 照片 | 主题 |
|---|---|---|
| 1 门口 | `stage1_gate_05.jpg` | 岭南牌坊：匾额高悬、石狮守门 |
| 2 前院 | `stage2_academy2_00.jpg` | 岭南书院实景：青砖黛瓦、镬耳山墙 |
| 3 讲堂 | `stage3_stone_29.jpg` | 讲堂楹联：梁柱之间读书 |
| 4 工坊 | `stage4_loom_12.jpg` | 手工织机：一梭一线织香云纱 |
| 5 尾声 | `stage5_courtyard_03.jpg` | 庭院一角：假山、水池、竹影 |

照片来源 Wikimedia Commons，供教学演示使用。

## 坐标约定（踩过坑，务必先读）
页面加载 GLB 时执行 `root.rotation.y = Math.PI`，所以：

**页面坐标 = (−x_blender, z_blender, −y_blender)**

实测各建筑位置（页面坐标）：

| 建筑 | z 范围 | 说明 |
|---|---|---|
| 门楼 | −32 .. −30 | 屋脊高 9.2m |
| 讲堂 | −28 .. −21 | Hi* 材质（讲案/书架/蒲团） |
| 六角亭 | −26 .. −18 | 立柱 + 亭顶 |
| 前院 | −14 .. −1 | Fc* 材质（碑廊/香炉/古井） |
| 工坊 | −12 .. −3 | Ws* 材质（织机/染缸/草编/工作台） |

> 改机位前，先在页面里按材质名统计一遍包围盒，不要直接套 Blender 建模坐标。

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
