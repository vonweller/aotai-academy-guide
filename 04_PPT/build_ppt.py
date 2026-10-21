# -*- coding: utf-8 -*-
"""生成《鳌台书院 AI 非遗导览》答辩 PPT

素材：
  05_Blender/qc/render_*.png   （Blender 场景渲染）
  03_网页3D/qc/*.png           （网页五关截图，Playwright 自动出图）
输出：04_PPT/鳌台书院AI非遗导览.pptx
"""
import os, glob
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

ROOT = os.path.dirname(os.path.abspath(__file__))          # 04_PPT
WS = os.path.dirname(ROOT)                                 # 项目根
OUT = os.path.join(WS, "04_PPT", "鳌台书院AI非遗导览.pptx")

INK = RGBColor(0x0D, 0x12, 0x14)
INK2 = RGBColor(0x16, 0x21, 0x26)
PAPER = RGBColor(0xF2, 0xEC, 0xE0)
GOLD = RGBColor(0xD9, 0xB4, 0x5B)
GOLD_D = RGBColor(0xB8, 0x91, 0x3F)
JADE = RGBColor(0x7F, 0xB3, 0xA1)
GREY = RGBColor(0x9A, 0x9A, 0x9A)
RED = RGBColor(0xC8, 0x45, 0x2F)

W, H = Inches(13.333), Inches(7.5)


def find(patterns):
    for p in patterns:
        hits = glob.glob(p, recursive=True)
        if hits:
            return sorted(hits)[0]
    return None


RENDERS = {
    "overview": find([os.path.join(WS, "05_Blender/qc/render_overview.png")]),
    "gate": find([os.path.join(WS, "05_Blender/qc/render_gate.png")]),
    "hall": find([os.path.join(WS, "05_Blender/qc/render_hall.png")]),
    "north": find([os.path.join(WS, "05_Blender/qc/render_north.png")]),
}
WEBSHOTS = sorted(glob.glob(os.path.join(WS, "03_网页3D/qc/*.png")))
print("renders:", {k: bool(v) for k, v in RENDERS.items()})
print("webshots:", len(WEBSHOTS))

prs = Presentation()
prs.slide_width = W
prs.slide_height = H
BLANK = prs.slide_layouts[6]


def bg(slide, color=INK):
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color


def bar(slide, l, t, w, h, color, alpha=None):
    sh = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, l, t, w, h)
    sh.fill.solid()
    sh.fill.fore_color.rgb = color
    sh.line.fill.background()
    return sh


def text(slide, s, l, t, w, h, size=20, color=PAPER, bold=False, align=PP_ALIGN.LEFT,
         font="微软雅黑", space_after=6, line=1.25):
    tb = slide.shapes.add_textbox(l, t, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = 0
    tf.margin_top = 0
    lines = s.split("\n")
    for i, ln in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(space_after)
        p.line_spacing = line
        r = p.add_run()
        r.text = ln
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.color.rgb = color
        r.font.name = font
    return tb


def bullets(slide, items, l, t, w, h, size=17, color=PAPER, dot_color=GOLD, gap=10):
    tb = slide.shapes.add_textbox(l, t, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = 0
    for i, it in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(gap)
        p.line_spacing = 1.28
        r = p.add_run()
        r.text = "▍ "
        r.font.size = Pt(size)
        r.font.color.rgb = dot_color
        r.font.name = "微软雅黑"
        r2 = p.add_run()
        r2.text = it
        r2.font.size = Pt(size)
        r2.font.color.rgb = color
        r2.font.name = "微软雅黑"
    return tb


def page_title(slide, title, sub=""):
    bar(slide, Inches(0.7), Inches(0.55), Inches(0.09), Inches(0.62), GOLD)
    text(slide, title, Inches(0.95), Inches(0.48), Inches(10), Inches(0.6), 30, PAPER, True)
    if sub:
        text(slide, sub, Inches(0.98), Inches(1.18), Inches(11.5), Inches(0.4), 14, GOLD)


def footer(slide, idx):
    text(slide, "鳌台书院 · AI 非遗导览  |  东莞厚街", Inches(0.7), Inches(6.95), Inches(8), Inches(0.3), 10, GREY)
    text(slide, "%02d" % idx, Inches(12.2), Inches(6.95), Inches(0.6), Inches(0.3), 10, GOLD, align=PP_ALIGN.RIGHT)


def pic_fit(slide, path, l, t, w, h, border=True):
    if not path or not os.path.exists(path):
        bar(slide, l, t, w, h, INK2)
        text(slide, "（待生成图片）", l + Inches(0.3), t + h / 2, w - Inches(0.6), Inches(0.4), 12, GREY)
        return None
    from PIL import Image
    try:
        iw, ih = Image.open(path).size
    except Exception:
        iw, ih = 16, 9
    ratio = min(float(w) / iw, float(h) / ih)
    nw, nh = int(iw * ratio), int(ih * ratio)
    nl = int(l + (w - nw) / 2)
    nt = int(t + (h - nh) / 2)
    pic = slide.shapes.add_picture(path, nl, nt, nw, nh)
    if border:
        pic.line.color.rgb = GOLD_D
        pic.line.width = Pt(1.2)
    return pic


idx = 0

# ---------------- 1 封面 ----------------
s = prs.slides.add_slide(BLANK); bg(s); idx += 1
if RENDERS["gate"]:
    pic_fit(s, RENDERS["gate"], 0, 0, W, H, border=False)
    bar(s, 0, 0, W, H, INK)
    # 半透明遮罩（用形状透明度）
    mask = bar(s, 0, 0, W, H, INK)
    mask.fill.transparency = 0.18
bar(s, Inches(0.9), Inches(2.1), Inches(0.1), Inches(2.6), GOLD)
text(s, "鳌 台 書 院", Inches(1.25), Inches(1.85), Inches(9), Inches(1.1), 54, PAPER, True, font="宋体")
text(s, "AI 非遗导览 · 粤地非遗物语", Inches(1.3), Inches(2.95), Inches(9), Inches(0.6), 24, GOLD)
text(s, "CyberCAM（K230）视觉交互  +  行空板 K10 语音唤醒  +  Blender 三维场景  +  Web 大屏联动",
     Inches(1.3), Inches(3.65), Inches(11), Inches(0.9), 14, PAPER)
text(s, "东莞厚街 · 岭南书院 · 五关式智能导览装置", Inches(1.3), Inches(4.35), Inches(9), Inches(0.4), 13, JADE)
text(s, "参赛团队：______________        指导老师：______________        2026",
     Inches(1.3), Inches(6.3), Inches(10), Inches(0.4), 12, GREY)
footer(s, idx)

# ---------------- 2 项目背景 ----------------
s = prs.slides.add_slide(BLANK); bg(s); idx += 1
page_title(s, "一、我们为什么做这件事", "岭南书院文化的“可见、可听、可玩”")
bullets(s, [
    "鳌台书院是东莞厚街的岭南书院代表，承载着明清以来的书香文脉；但展陈以静态图文为主，青少年“看一眼就走”。",
    "非遗（香云纱、莞草编织、千角灯……）同样面临“知道名字、不知道故事”的困境。",
    "我们希望把“AI + 非遗 + 实体模型”做成一套可复制的导览装置：人会说话、书院会回应、观众能被“带着走”。",
    "技术路线选择国产开源硬件：CyberCAM（K230，6TOPS AI 算力）负责看，行空板 K10（ESP32-S3）负责听与说。",
], Inches(1.1), Inches(1.9), Inches(11.2), Inches(3.6), 17)
bar(s, Inches(1.1), Inches(5.55), Inches(11.1), Emu(9525), GOLD_D)
text(s, "一句话：让每一位走进书院的观众，都有一个“AI 导览员小鳌”全程陪着走五关。",
     Inches(1.1), Inches(5.75), Inches(11.2), Inches(0.5), 16, GOLD)
footer(s, idx)

# ---------------- 3 总体方案 ----------------
s = prs.slides.add_slide(BLANK); bg(s); idx += 1
page_title(s, "二、总体方案：三端一体的导览装置", "CyberCAM 看 · K10 听 · 大屏走")
# 三列
cards = [
    ("CyberCAM（K230）", ["KPU 人脸检测（320 模型）", "LBPH 人脸识别（现场可注册）", "640×480 自绘五关 UI", "双语 TTS 播报（粤语/普通话）", "MQTT 上报事件"]),
    ("行空板 K10", ["语音唤醒「你好小行」", "关键词：下一关/上一关/重播", "粤语 · 普通话切换", "1.3 寸屏显示关卡状态", "按键 + RGB 状态指示"]),
    ("PC 网页 3D", ["Blender 复刻鳌台书院", "书生小鳌沿路径行走", "五关交互与问答面板", "Flask + MQTT 实时联动", "投影/电视大屏展示"]),
]
x = Inches(0.8)
for title, items in cards:
    card = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, Inches(1.85), Inches(3.85), Inches(4.4))
    card.fill.solid(); card.fill.fore_color.rgb = INK2
    card.line.color.rgb = GOLD_D; card.line.width = Pt(1)
    text(s, title, x + Inches(0.25), Inches(2.05), Inches(3.4), Inches(0.5), 18, GOLD, True)
    y = Inches(2.65)
    for it in items:
        text(s, "· " + it, x + Inches(0.25), y, Inches(3.4), Inches(0.5), 12.5, PAPER)
        y += Inches(0.52)
    x += Inches(4.1)
text(s, "三者通过 MQTT（aotai/state · aotai/event · aotai/cmd）实时同步：谁先动，其他的都跟着动。",
     Inches(0.85), Inches(6.42), Inches(11.5), Inches(0.4), 13, JADE)
footer(s, idx)

# ---------------- 4 硬件与接线 ----------------
s = prs.slides.add_slide(BLANK); bg(s); idx += 1
page_title(s, "三、硬件设计与连接", "国产开源硬件 · 低门槛可复制")
bullets(s, [
    "主控 A：CyberCAM（嘉楠 K230，RISC-V 双核 + 6TOPS KPU，Debian + Python3），2.4 寸 640×480 触摸屏、CSI2 摄像头、板载扬声器。",
    "主控 B：行空板 K10（ESP32-S3 N16R8），1.3 寸屏、双麦、RGB 灯、A/B 按键，跑 Arduino 固件做语音唤醒与关键词识别。",
    "网络：同一 WiFi 局域网；PC 端同时运行 MQTT Broker 与 Flask 网页服务，CyberCAM / K10 均作为 MQTT 客户端接入。",
    "音频：语音素材提前用 TTS 合成好的 mp3，按语言分目录缓存在 CyberCAM 本地，无网也能完整播报。",
], Inches(1.1), Inches(1.95), Inches(6.3), Inches(4.2), 16)
# 右侧示意图
box_l = Inches(7.6)
for i, (name, sub) in enumerate([
    ("电脑 PC", "MQTT Broker + Flask 网页"),
    ("CyberCAM", "视觉 / UI / 语音"),
    ("行空板 K10", "语音唤醒 / 关键词"),
]):
    yy = Inches(2.0 + i * 1.45)
    r = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, box_l, yy, Inches(4.9), Inches(1.05))
    r.fill.solid(); r.fill.fore_color.rgb = INK2
    r.line.color.rgb = GOLD_D
    text(s, name, box_l + Inches(0.25), yy + Inches(0.14), Inches(4), Inches(0.4), 15, GOLD, True)
    text(s, sub, box_l + Inches(0.25), yy + Inches(0.55), Inches(4.4), Inches(0.35), 11, PAPER)
    if i < 2:
        text(s, "⇅ MQTT", box_l + Inches(4.2), yy + Inches(1.08), Inches(1), Inches(0.3), 10, JADE)
text(s, "接线：CyberCAM 与 K10 各自独立供电（USB-C 5V），无需互相连线，全部走网络。",
     Inches(1.1), Inches(6.3), Inches(11), Inches(0.4), 12, GREY)
footer(s, idx)

# ---------------- 5 五关流程 ----------------
s = prs.slides.add_slide(BLANK); bg(s); idx += 1
page_title(s, "四、五关式导览流程", "门槛递进：看脸 → 听史 → 读联 → 识艺 → 留愿")
stages = [
    ("第一关", "门口迎宾", "人脸识别", "CyberCAM 检测到人脸即进入识别；识别成功播报“预约访客，欢迎您来到非遗博物馆AI鳌台书院”"),
    ("第二关", "前院溯源", "建院故事", "明代成化十二年王恪倡建 → 清代迁建菊山 → 2008 重建；AI 出题三选一"),
    ("第三关", "讲堂楹联", "楹联诵读", "“学贵因时，通古今之谓士；地原毓秀，树梁栋以成材”，领读 + 释义"),
    ("第四关", "非遗工坊", "香云纱·莞草", "薯莨浸染 + 河泥覆盖的香云纱，咸水草编织的莞草器物；第二轮问答"),
    ("第五关", "尾声留墨", "结语与路线", "主题曲式结语 + 推荐参观路线，可一键重置重新开始"),
]
y = Inches(1.75)
for i, (no, name, tag, desc) in enumerate(stages):
    chip = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.85), y, Inches(1.15), Inches(0.86))
    chip.fill.solid(); chip.fill.fore_color.rgb = GOLD if i == 0 else INK2
    chip.line.color.rgb = GOLD_D
    text(s, no, Inches(0.85), y + Inches(0.22), Inches(1.15), Inches(0.4), 14,
         INK if i == 0 else GOLD, True, PP_ALIGN.CENTER)
    text(s, name + " · " + tag, Inches(2.2), y + Inches(0.02), Inches(3), Inches(0.4), 15, PAPER, True)
    text(s, desc, Inches(2.2), y + Inches(0.42), Inches(10.1), Inches(0.45), 11.5, GREY)
    y += Inches(1.0)
footer(s, idx)

# ---------------- 6 Blender 三维复刻 ----------------
s = prs.slides.add_slide(BLANK); bg(s); idx += 1
page_title(s, "五、三维复刻：用 Blender 重建鳌台书院", "程序化建模 → glTF 导出 → Three.js 实时渲染")
pic_fit(s, RENDERS.get("overview"), Inches(0.7), Inches(1.75), Inches(7.4), Inches(4.3))
bullets(s, [
    "按岭南书院形制建模：门楼牌坊「鰲台書院」、石狮、云墙漏窗、前院天井水池假山、硬山顶讲堂、非遗工坊、六角亭。",
    "纯 Python 脚本生成（build_academy.py），参数化可复现；导出 GLB 约 1.4 MB，2.2 万面，网页秒开。",
    "网页端用 Three.js 加载同一份 GLB，保留实时阴影与光照。",
    "附 4 张固定机位渲染图，用于 PPT 与展板。",
], Inches(8.4), Inches(1.95), Inches(4.3), Inches(4.0), 13.5)
footer(s, idx)

# ---------------- 7 网页交互 ----------------
s = prs.slides.add_slide(BLANK); bg(s); idx += 1
page_title(s, "六、网页 3D 交互大屏", "点一下「下一关」，小鳌就自己走过去")
shots = WEBSHOTS[:3]
xs = [Inches(0.7), Inches(4.75), Inches(8.8)]
labels = ["门口：人脸识别", "前院：问答", "讲堂：楹联"]
for i in range(3):
    pic_fit(s, shots[i] if i < len(shots) else None, xs[i], Inches(1.8), Inches(3.9), Inches(2.5))
    text(s, labels[i] if i < len(labels) else "", xs[i], Inches(4.4), Inches(3.9), Inches(0.35), 11, GOLD)
bullets(s, [
    "小鳌（Q 版书生）站在门口；点「下一关」后沿 Catmull-Rom 曲线平滑行走，边走边播放该关讲解。",
    "五关面板、三选一问答、字幕、进度条、语言切换（粤语/普通话）全部在网页内完成。",
    "键盘 N/P/空格/L/R/1-5 与鼠标按钮等价，适合评委现场自由演示。",
    "通过 Flask + MQTT 与硬件联动：CyberCAM 识别成功 → 网页自动亮起；K10 说「下一关」→ 网页跟着走。",
], Inches(0.75), Inches(4.95), Inches(12), Inches(1.8), 13)
footer(s, idx)

# ---------------- 8 CyberCAM ----------------
s = prs.slides.add_slide(BLANK); bg(s); idx += 1
page_title(s, "七、CyberCAM：看得见、说得出", "K230 上跑 Python，一人一屏一整套导览")
bullets(s, [
    "视觉：KPU FACE_DETECT（320 检测模型）+ OpenCV LBPH 识别，现场按 K 键即可把人脸注册进“预约访客”。",
    "交互：640×480 自绘 UI（文泉驿字体 + 触摸标定），首屏语言选择，五关状态机，问答按钮与字幕。",
    "语音：本地 mp3 优先播放（aplay 直出板载喇叭），缺失时在线 TTS 合成并缓存；粤语/普通话各一套。",
    "网络：paho-mqtt 把 face_detected / face_recognized / stage_enter / speak 等事件发到 aotai/event。",
    "降级：无摄像头无网络时进入演示模式，仍可完整走完五关（答辩保险）。",
], Inches(1.1), Inches(1.95), Inches(11.3), Inches(4.4), 16)
footer(s, idx)

# ---------------- 9 K10 ----------------
s = prs.slides.add_slide(BLANK); bg(s); idx += 1
page_title(s, "八、行空板 K10：听得懂、叫得应", "离线语音唤醒 + 关键词识别 + 状态屏")
bullets(s, [
    "唤醒词：「你好小行 / 你好小新」；唤醒后 12 秒内说指令。",
    "关键词（拼音指令串）：下一关、上一关、重播、普通话、粤语、重新开始、人脸识别。",
    "屏幕：当前关卡 / 语言 / WiFi 与 MQTT 状态 / 最近识别的指令；A 键下一关，B 键切语言，A+B 重播。",
    "RGB：普通话金色、粤语青绿、断网暗红，评委一眼看得出状态。",
    "所有指令经 MQTT 广播，CyberCAM 与网页同时响应 —— 说一句，全场动。",
], Inches(1.1), Inches(1.95), Inches(11.3), Inches(4.4), 16)
footer(s, idx)

# ---------------- 10 软件架构 ----------------
s = prs.slides.add_slide(BLANK); bg(s); idx += 1
page_title(s, "九、软件架构与通信协议", "三条链路：事件流 / 控制流 / 状态流")
rows = [
    ("aotai/state", "保留状态", "stage、lang、face_ok、visitor", "所有端订阅，网页启动即同步"),
    ("aotai/event", "事件流", "face_detected、face_recognized、stage_enter、speak…", "CyberCAM / K10 → PC 桥 → 网页"),
    ("aotai/cmd", "控制流", "next、prev、set_lang、goto_stage、speak、reset", "网页 / K10 → CyberCAM"),
    ("aotai/web", "看板操作", "goto、speak、reset", "网页 → 全网"),
]
ty = Inches(1.85)
bar(s, Inches(0.85), ty, Inches(11.6), Inches(0.45), GOLD_D)
for i, h in enumerate(["主题", "类型", "消息", "说明"]):
    text(s, h, Inches(0.95 + i * 3.0), ty + Inches(0.08), Inches(2.9), Inches(0.35), 13, INK, True)
ty += Inches(0.5)
for t, k, m, d in rows:
    bar(s, Inches(0.85), ty, Inches(11.6), Inches(0.02), RGBColor(0x33, 0x33, 0x33))
    text(s, t, Inches(0.95), ty + Inches(0.12), Inches(2.9), Inches(0.4), 11.5, GOLD, True)
    text(s, k, Inches(3.95), ty + Inches(0.12), Inches(2.9), Inches(0.4), 11.5, PAPER)
    text(s, m, Inches(6.95), ty + Inches(0.12), Inches(3.4), Inches(0.6), 10.5, JADE)
    text(s, d, Inches(10.4), ty + Inches(0.12), Inches(2.1), Inches(0.6), 9.5, GREY)
    ty += Inches(0.72)
text(s, "PC 端：Flask 提供静态站点 + /api/state + SSE 实时推送；内置零依赖 MQTT Broker，现场一台电脑即可跑通全部演示。",
     Inches(0.9), Inches(6.1), Inches(11.6), Inches(0.6), 12, GREY)
footer(s, idx)

# ---------------- 11 创新点 ----------------
s = prs.slides.add_slide(BLANK); bg(s); idx += 1
page_title(s, "十、创新点", "不是“做一个 Demo”，而是把三块能力焊在一起")
items = [
    ("① 五关式递进导览", "把书院文化拆成看脸入场、溯源、读联、识艺、留愿五个关卡，观众有目标感、有完成感。"),
    ("② 实体模型 + 虚拟场景同构", "网页 3D 与实物模型用同一套关卡坐标（map.json），手动摆小人 ↔ 点一下“下一关”，线上线下同步推进。"),
    ("③ 双主控异构协同", "CyberCAM 负责重算力视觉与 UI，K10 负责轻量语音唤醒；各司其职、MQTT 解耦，任一环节可单独替换。"),
    ("④ 离线优先的双语语音", "55 条粤语/普通话语音预生成缓存在本地，无网也能完整讲解；缺失时才在线合成。"),
    ("⑤ 答辩级容错", "人脸、摄像头、MQTT、网页后端任一环节故障都会自动降级，演示不中断。"),
]
y = Inches(1.8)
for t, d in items:
    bar(s, Inches(0.85), y + Inches(0.08), Inches(0.08), Inches(0.5), GOLD)
    text(s, t, Inches(1.1), y, Inches(4.2), Inches(0.4), 15, GOLD, True)
    text(s, d, Inches(5.0), y, Inches(7.5), Inches(0.8), 12.5, PAPER)
    y += Inches(1.0)
footer(s, idx)

# ---------------- 12 演示流程 ----------------
s = prs.slides.add_slide(BLANK); bg(s); idx += 1
page_title(s, "十一、现场演示脚本（3 分钟）", "照着念就能演完")
steps = [
    "00:00  电脑运行 run_demo.py，投影出现网页开场页；讲解员站到 CyberCAM 前。",
    "00:15  CyberCAM 识别到人脸 → 播报“预约访客，欢迎您来到非遗博物馆AI鳌台书院”；网页同步亮起识别成功。",
    "00:40  对 K10 说「你好小行」→「下一关」；网页小鳌开始走向前院，K10 屏幕显示第 2 关。",
    "01:10  前院问答三选一，观众按屏幕或说答案；答对后小鳌继续走向讲堂。",
    "01:40  讲堂楹联领读；K10 说「粤语」，全场语音立即切换成粤语。",
    "02:10  非遗工坊问答 + 尾声留墨；手动把实物小人摆到下一关，网页点「下一关」同步跟上。",
    "02:45  说「重新开始」或按 R，回到第一关，欢迎下一位观众。",
]
y = Inches(1.8)
for st in steps:
    text(s, st, Inches(1.0), y, Inches(11.3), Inches(0.5), 13.5, PAPER)
    y += Inches(0.66)
bar(s, Inches(1.0), Inches(6.5), Inches(11.3), Emu(9525), GOLD_D)
text(s, "备用方案：任何硬件异常，直接用网页键盘演示（N/P/L/R/1-5），功能完整不掉链子。",
     Inches(1.0), Inches(6.6), Inches(11.3), Inches(0.4), 11, JADE)
footer(s, idx)

# ---------------- 13 下一步 ----------------
s = prs.slides.add_slide(BLANK); bg(s); idx += 1
page_title(s, "十二、迭代方向", "从一个书院，到一片岭南")
bullets(s, [
    "内容扩展：接入大模型做开放问答（RAG 知识库：书院志、东莞非遗名录），支持自由提问而非固定三选一。",
    "识别升级：CyberCAM 训练非遗器物识别模型（香云纱、莞草篮、千角灯），走到工坊即可“拿起即讲”。",
    "多语种：在粤语/普通话之外增加英语，服务大湾区与海外观众。",
    "装置化：把三端打包进一个可搬动的展台（含 UPS、投影、音响），可在不同学校、展馆巡展。",
    "数据化：统计观众停留时长、答题正确率、最常走路线，反哺展陈设计。",
], Inches(1.1), Inches(1.95), Inches(11.3), Inches(4.4), 16)
footer(s, idx)

# ---------------- 14 致谢 ----------------
s = prs.slides.add_slide(BLANK); bg(s); idx += 1
if RENDERS.get("gate"):
    pic_fit(s, RENDERS["gate"], 0, 0, W, H, border=False)
    mask = bar(s, 0, 0, W, H, INK)
    mask.fill.transparency = 0.25
text(s, "谢 谢 聆 听", Inches(0), Inches(2.7), W, Inches(1.0), 48, PAPER, True, PP_ALIGN.CENTER, font="宋体")
text(s, "鳌台书院 · AI 非遗导览  ·  粤地非遗物语", Inches(0), Inches(3.85), W, Inches(0.5), 20, GOLD, False, PP_ALIGN.CENTER)
text(s, "CyberCAM × 行空板 K10 × Blender × Three.js", Inches(0), Inches(4.5), W, Inches(0.4), 14, JADE, False, PP_ALIGN.CENTER)
footer(s, idx)

os.makedirs(ROOT, exist_ok=True)
prs.save(OUT)
print("PPT saved:", OUT, os.path.getsize(OUT) // 1024, "KB, slides:", len(prs.slides))
