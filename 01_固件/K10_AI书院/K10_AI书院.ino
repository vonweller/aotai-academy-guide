/*
 * 鳌台书院 AI 非遗导览 · 行空板 K10 语音交互终端
 * ------------------------------------------------------------
 * 功能：
 *   1) 离线语音唤醒（你好小行 / 你好小新）+ 中文关键词识别
 *   2) 关键词：下一关 / 上一关 / 重播 / 普通话 / 粤语 / 重新开始 / 人脸识别 / 说明
 *   3) 指令经 MQTT 广播：aotai/k10（事件）与 aotai/cmd（控制），CyberCAM / 网页同时响应
 *   4) 屏幕显示当前关卡、语言、网络状态、最近一条指令；A/B/A+B 按键可物理操作
 *
 * 编译烧录（Windows Git Bash；中文识别必须带 CN 模型）：
 *   K10_MODEL=Hi_eps bash ~/.agents/skills/arduino-esp32s3-k10-xiaosense/scripts/compile-k10.sh \
 *     "D:/.../01_固件/K10_AI书院" COM12
 *
 * 关键 API（按 BSP 例程，勿自造）：
 *   asr.asrInit(CONTINUOUS, CN_MODE, 6000);
 *   asr.isWakeUp();  asr.isDetectCmdID(id);  asr.speak("中文");
 *   k10.canvas->canvasText(String, row, color);  k10.canvas->updateCanvas();
 */
#include <WiFi.h>
#include <PubSubClient.h>
#include "asr.h"
#include "unihiker_k10.h"
#include "secrets.h"

// ---------------- 配置 ----------------
#define TOPIC_STATE "aotai/state"
#define TOPIC_EVENT "aotai/event"
#define TOPIC_CMD   "aotai/cmd"
#define TOPIC_K10   "aotai/k10"

UNIHIKER_K10 k10;
ASR asr;
WiFiClient net;
PubSubClient mqtt(net);

uint8_t screen_dir = 2;

// ---------------- 运行时状态 ----------------
int g_stage = 1;
int g_lang = 0;                 // 0=普通话 1=粤语
bool g_waked = false;
unsigned long g_wakeMs = 0;
String g_lastCmd = "";
String g_status = "启动中";

// 待播报（绝不在 MQTT 回调里 speak）
static String g_sayQueue[8];
static int g_sayHead = 0, g_sayTail = 0;

// 屏幕刷新节流
static int g_drawnStage = -1, g_drawnLang = -1, g_drawnMqtt = -1;
static String g_drawnStatus = "", g_drawnCmd = "", g_drawnWake = "";

void sayPush(const String &s) {
  (void)s;   // 本地不播报（见 sayLoop 注释）
}

// K10 不做本地 TTS（ASR 库的 TTS 队列在部分固件上会 assert）
// 播报统一由 CyberCAM 负责，K10 只发 MQTT 指令
void sayLoop() {
  g_sayHead = g_sayTail;   // 丢弃队列
}

// ---------------- 网络 ----------------
void connectWifi() {
  if (WiFi.status() == WL_CONNECTED) return;
  g_status = "连接WiFi..";
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  unsigned long t0 = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - t0 < 12000) delay(300);
  g_status = (WiFi.status() == WL_CONNECTED) ? "WiFi已连" : "WiFi失败";
}

// ---------- 极简 JSON（不依赖 ArduinoJson，避免版本差异） ----------
String jsonEsc(const String &in) {
  String o = "";
  for (size_t i = 0; i < in.length(); i++) {
    char c = in[i];
    if (c == '"' || c == '\\') { o += '\\'; o += c; }
    else if (c == '\n') o += "\\n";
    else o += c;
  }
  return o;
}

String jsonGet(const String &src, const char *key) {
  String k = String("\"") + key + "\"";
  int i = src.indexOf(k);
  if (i < 0) return "";
  i = src.indexOf(':', i + k.length());
  if (i < 0) return "";
  i++;
  while (i < (int)src.length() && (src[i] == ' ' || src[i] == '\t')) i++;
  if (i >= (int)src.length()) return "";
  if (src[i] == '"') {
    int j = src.indexOf('"', i + 1);
    if (j < 0) return "";
    return src.substring(i + 1, j);
  }
  int j = i;
  while (j < (int)src.length() && src[j] != ',' && src[j] != '}') j++;
  return src.substring(i, j);
}

void publishState() {
  if (!mqtt.connected()) return;
  String p = String("{\"stage\":") + g_stage +
             ",\"lang\":\"" + (g_lang == 0 ? "zh" : "yue") +
             "\",\"source\":\"" + DEVICE_ID + "\"}";
  mqtt.publish(TOPIC_STATE, p.c_str(), false);
}

void publishK10(const char *type, const char *cmd, const char *text) {
  if (!mqtt.connected()) return;
  String p = String("{\"type\":\"") + type + "\"";
  if (cmd && cmd[0])  p += String(",\"cmd\":\"") + jsonEsc(String(cmd)) + "\"";
  if (text && text[0]) p += String(",\"text\":\"") + jsonEsc(String(text)) + "\"";
  p += String(",\"lang\":\"") + (g_lang == 0 ? "zh" : "yue") + "\"";
  p += String(",\"stage\":") + g_stage + ",\"source\":\"" + DEVICE_ID + "\"}";
  mqtt.publish(TOPIC_K10, p.c_str(), false);
}

void publishCmd(const char *cmd, int stage, const char *lang) {
  if (!mqtt.connected()) return;
  String p = String("{\"cmd\":\"") + cmd + "\"";
  if (stage > 0) p += String(",\"stage\":") + stage;
  if (lang && lang[0]) p += String(",\"lang\":\"") + lang + "\"";
  p += String(",\"source\":\"") + DEVICE_ID + "\"}";
  mqtt.publish(TOPIC_CMD, p.c_str(), false);
}

void onMqttMessage(char *topic, byte *payload, unsigned int len) {
  if (len == 0 || len > 512) return;
  String body = "";
  for (unsigned int i = 0; i < len; i++) body += (char)payload[i];
  String t = String(topic);
  if (t == TOPIC_STATE) {
    String st = jsonGet(body, "stage");
    String lg = jsonGet(body, "lang");
    if (st.length()) g_stage = st.toInt();
    if (lg.length()) g_lang = (lg == "yue") ? 1 : 0;
  } else if (t == TOPIC_CMD) {
    String c = jsonGet(body, "cmd");
    g_lastCmd = c;
    if (c == "next") g_stage = min(5, g_stage + 1);
    else if (c == "prev") g_stage = max(1, g_stage - 1);
    else if (c == "goto_stage") g_stage = jsonGet(body, "stage").toInt();
    else if (c == "set_lang") g_lang = (jsonGet(body, "lang") == "yue") ? 1 : 0;
    else if (c == "reset") g_stage = 1;
    else if (c == "speak") {
      String txt = jsonGet(body, "text");
      if (txt.length()) sayPush(txt);
    }
  }
}

void connectMqtt() {
  if (WiFi.status() != WL_CONNECTED || mqtt.connected()) return;
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setCallback(onMqttMessage);
  mqtt.setBufferSize(768);
  g_status = "MQTT连接..";
  bool ok = (strlen(MQTT_USER) > 0) ? mqtt.connect(DEVICE_ID, MQTT_USER, MQTT_PASS)
                                    : mqtt.connect(DEVICE_ID);
  if (ok) {
    mqtt.subscribe(TOPIC_STATE);
    mqtt.subscribe(TOPIC_CMD);
    g_status = "MQTT已连";
    publishState();
    publishK10("k10_status", "", "");
  } else {
    g_status = "MQTT未连";
  }
}

// ---------------- 语音指令 ----------------
void setupAsr() {
  asr.asrInit(CONTINUOUS, CN_MODE, 6000);   // 连续识别 + 中文 + 唤醒 6s
  unsigned long t0 = millis();
  while (asr._asrState == 0 && millis() - t0 < 8000) delay(100);
  asr.addASRCommand(1, "xia yi guan");
  asr.addASRCommand(2, "shang yi guan");
  asr.addASRCommand(3, "chong bo");
  asr.addASRCommand(4, "pu tong hua");
  asr.addASRCommand(5, "yue yu");
  asr.addASRCommand(6, "chong xin kai shi");
  asr.addASRCommand(7, "ren lian shi bie");
  asr.addASRCommand(8, "shuo ming");
}

void handleCmdId(int id) {
  const char *cn = "";
  const char *say = "";
  switch (id) {
    case 1: cn = "下一关";  g_stage = min(5, g_stage + 1); publishCmd("next", 0, "");  say = "好，我们前往下一关。"; break;
    case 2: cn = "上一关";  g_stage = max(1, g_stage - 1); publishCmd("prev", 0, "");  say = "回到上一关。"; break;
    case 3: cn = "重播";    publishCmd("repeat", 0, "");                              say = "好的，重播这一关的讲解。"; break;
    case 4: cn = "普通话";  g_lang = 0; publishCmd("set_lang", 0, "zh");               say = "好的，改用普通话。"; break;
    case 5: cn = "粤语";    g_lang = 1; publishCmd("set_lang", 0, "yue");              say = "好，改用粵語。"; break;
    case 6: cn = "重新开始"; g_stage = 1; publishCmd("reset", 0, "");                  say = "好的，我们重新开始。"; break;
    case 7: cn = "人脸识别"; publishCmd("goto_stage", 1, "");                          say = "请正对镜头，准备人脸识别。"; break;
    case 8: cn = "说明";    say = "可以说下一关、上一关、重播、粤语或者普通话。"; break;
    default: return;
  }
  g_lastCmd = String(cn);
  publishK10("voice_cmd", cn, cn);
  publishState();
  sayPush(String(say));
}

// ---------------- 屏幕 ----------------
void drawScreen(bool force = false) {
  int mqttOn = mqtt.connected() ? 1 : 0;
  String wake = g_waked ? "已唤醒，说指令" : "说「你好小行」唤醒";
  if (!force && g_drawnStage == g_stage && g_drawnLang == g_lang &&
      g_drawnMqtt == mqttOn && g_drawnStatus == g_status &&
      g_drawnCmd == g_lastCmd && g_drawnWake == wake) {
    return;
  }
  g_drawnStage = g_stage; g_drawnLang = g_lang; g_drawnMqtt = mqttOn;
  g_drawnStatus = g_status; g_drawnCmd = g_lastCmd; g_drawnWake = wake;

  k10.canvas->canvasClear();
  k10.canvas->canvasText("鳌台书院 · AI导览", 1, 0xF2E8CF);
  k10.canvas->canvasText("第 " + String(g_stage) + " 关 / 5", 2, 0xD9B45B);
  k10.canvas->canvasText(g_lang == 0 ? "语言：普通话" : "语言：粤语", 3, 0x9ED8C4);
  k10.canvas->canvasText(String("WiFi:") + (WiFi.status() == WL_CONNECTED ? "OK" : "--") +
                         "  MQTT:" + (mqttOn ? "OK" : "--"), 4, 0xFFFFFF);
  k10.canvas->canvasText(g_status, 5, 0xAAAAAA);
  k10.canvas->canvasText("─────────────", 6, 0x555555);
  k10.canvas->canvasText(wake, 7, 0xD9B45B);
  k10.canvas->canvasText("下一关 / 上一关 / 重播", 8, 0xFFFFFF);
  k10.canvas->canvasText("普通话 / 粤语 / 重新开始", 9, 0xFFFFFF);
  if (g_lastCmd.length()) k10.canvas->canvasText("最近：" + g_lastCmd, 10, 0x7FB3A1);
  k10.canvas->updateCanvas();
}

void updateRgb() {
  if (!mqtt.connected()) {
    k10.rgb->write(-1, 0xAA2222);
  } else if (g_lang == 1) {
    k10.rgb->write(-1, 0x00AA55);
  } else {
    k10.rgb->write(-1, 0xD9B45B);
  }
}

void pollButtons() {
  if (k10.buttonA->isPressed()) {   // A = 下一关
    handleCmdId(g_waked ? 1 : 1);
    delay(300);
  }
  if (k10.buttonB->isPressed()) {   // B = 切语言
    handleCmdId(g_lang == 0 ? 5 : 4);
    delay(300);
  }
  if (k10.buttonAB->isPressed()) {  // A+B = 重播
    handleCmdId(3);
    delay(300);
  }
}

// ---------------- setup / loop ----------------
void setup() {
  Serial.begin(115200);
  delay(400);
  Serial.println();
  Serial.println("[AOTAI] boot, wifi=" WIFI_SSID " mqtt=" MQTT_HOST);
  k10.begin();
  setupAsr();
  k10.initScreen(screen_dir);
  k10.creatCanvas();
  k10.rgb->brightness(5);
  k10.rgb->write(-1, 0xD9B45B);
  connectWifi();
  Serial.printf("[AOTAI] wifi status=%d ip=%s rssi=%d\n", (int)WiFi.status(),
                WiFi.localIP().toString().c_str(), WiFi.RSSI());
  connectMqtt();
  Serial.printf("[AOTAI] mqtt connected=%d state=%d\n", mqtt.connected(), mqtt.state());
  g_status = mqtt.connected() ? "就绪" : "离线运行";
  drawScreen(true);
  sayPush("鳌台书院导览终端已启动。");
}

void loop() {
  // WiFi / MQTT 保活
  if (WiFi.status() != WL_CONNECTED) {
    static unsigned long lastWifi = 0;
    if (millis() - lastWifi > 15000) {
      lastWifi = millis();
      Serial.printf("[AOTAI] wifi down status=%d, reconnecting\n", (int)WiFi.status());
      WiFi.disconnect(true);
      connectWifi();
      Serial.printf("[AOTAI] after retry status=%d ip=%s\n", (int)WiFi.status(),
                    WiFi.localIP().toString().c_str());
    }
  }
  if (!mqtt.connected()) {
    static unsigned long lastMqtt = 0;
    if (millis() - lastMqtt > 5000) { lastMqtt = millis(); connectMqtt(); }
  }
  mqtt.loop();

  // 唤醒
  if (asr.isWakeUp()) {
    g_waked = true;
    g_wakeMs = millis();
    publishK10("wake", "", "");
    sayPush("我在，请说指令。");
  }
  // 关键词（isDetectCmdID 读完即清，逐个试）
  for (int id = 1; id <= 8; id++) {
    if (asr.isDetectCmdID(id)) {
      handleCmdId(id);
      break;
    }
  }
  if (g_waked && millis() - g_wakeMs > 12000) g_waked = false;

  // 心跳：每 10s 上报一次，网页/PC 用来看设备在线
  static unsigned long lastBeat = 0;
  if (millis() - lastBeat > 10000) {
    lastBeat = millis();
    publishState();
    publishK10("heartbeat", "", "");
  }

  sayLoop();          // 只在 loop 里 speak
  pollButtons();
  drawScreen();
  updateRgb();
  delay(30);
}
