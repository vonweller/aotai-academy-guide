# -*- coding: utf-8 -*-
"""鳌台书院 AI 非遗导览 · CyberCAM 全局配置
不改逻辑时只改这里。现场按实际 WiFi / PC IP 调整 MQTT_HOST。
"""
import os

# ---------- 网络 ----------
WIFI_SSID = os.environ.get("AOTAI_WIFI_SSID", "LYT")
WIFI_PASSWORD = os.environ.get("AOTAI_WIFI_PASS", "lyt13509018386")

MQTT_HOST = os.environ.get("AOTAI_MQTT_HOST", "159.75.137.223")   # LYT 现场：公共 MQTT
WEB_PUSH = os.environ.get("AOTAI_WEB_PUSH", "http://192.168.10.66:8000/api/camera")
MQTT_PORT = int(os.environ.get("AOTAI_MQTT_PORT", "1883"))
MQTT_USER = os.environ.get("AOTAI_MQTT_USER", "siot")
MQTT_PASS = os.environ.get("AOTAI_MQTT_PASS", "dfrobot")
CLIENT_ID = "cybercam-01"

TOPIC_STATE = "aotai/state"
TOPIC_EVENT = "aotai/event"
TOPIC_CMD = "aotai/cmd"
TOPIC_K10 = "aotai/k10"
TOPIC_WEB = "aotai/web"

# ---------- 路径 ----------
APP_DIR = "/data/app/aotai"
DATA_DIR = "/data/aotai"                      # 媒体盘可写目录（音频/人脸库）
# PC/IDE 调试时数据目录回退（存在就优先用，方便离线生成音频后直接预览）
_HERE = os.path.dirname(os.path.abspath(__file__))
_LOCAL_DATA = os.path.join(_HERE, "..", "..", "02_数据")
if os.path.isdir(os.path.join(_LOCAL_DATA, "audio")):
    DATA_DIR = os.path.abspath(_LOCAL_DATA)
CONTENT_PATH = os.path.join(DATA_DIR, "content.json")
AUDIO_DIR = os.path.join(DATA_DIR, "audio")   # audio/{zh|yue}/{id}.mp3
FACE_DB_DIR = os.path.join(DATA_DIR, "faces") # LBPH 人脸库 + labels.json
RELIC_MODEL = os.path.join(DATA_DIR, "relics", "model.npz")

# 官方预装人脸检测模型（复用，不必拷）
FACE_KMODEL_CANDIDATES = [
    "./face_detection_320.kmodel",
    "/data/app/face-det/face_detection_320.kmodel",
]
FACE_ANCHORS_CANDIDATES = [
    "./prior_data_320.bin",
    "/data/app/face-det/prior_data_320.bin",
]

# 本地内置的兜底文案（content.json 缺失时用）
FALLBACK_LANG = "zh"
LANGS = ("zh", "yue")
LANG_NAME = {"zh": "普通话", "yue": "粤语"}

# ---------- 人脸识别 ----------
FACE_RELIABILITY = 0.6
FACE_NMS = 0.7
FACE_MIN_SIZE = 90            # 框小于该像素视为太远，不识别
RECOG_INTERVAL = 1.2          # 秒，两次识别间隔（太长会一直停在"检测到人脸"）
RECOG_CONFIRM_FRAMES = 2      # 连续命中次数才算识别成功
LBPH_THRESHOLD = 130.0        # 距离阈值。实测本人 26~125、外人 153，取 130 兼顾两边
AUTO_ENROLL_SECONDS = 0       # >0 时：无人脸库时自动把第一张脸录为"预约访客"

# ---------- 关卡 ----------
STAGE_MAX = 5
STAGE_NAMES = {
    1: {"zh": "第一关 · 门口迎宾", "yue": "第一關 · 門口迎賓"},
    2: {"zh": "第二关 · 鳌台溯源", "yue": "第二關 · 鰲台溯源"},
    3: {"zh": "第三关 · 讲堂楹联", "yue": "第三關 · 講堂楹聯"},
    4: {"zh": "第四关 · 非遗工坊", "yue": "第四關 · 非遺工坊"},
    5: {"zh": "第五关 · 留墨寄愿", "yue": "第五關 · 留墨寄願"},
}

# ---------- 播放 ----------
AUDIO_CMD = ["aplay", "-q", "-D", "plughw:K230I2SINNO"]   # 若声卡名不同，改成 plughw:0,0
VOLUME = 90

# ---------- UI ----------
SCREEN_W, SCREEN_H = 640, 480
FONT_PATH = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
UI_FPS = 20          # 有摄像头的页面（人脸/火眼金睛）
UI_FPS_IDLE = 8      # 静态页面（语言/功能/关卡），省 CPU
