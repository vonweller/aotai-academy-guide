# 行空板 K10 · 语音交互终端

## 编译烧录
```bash
K10_MODEL=Hi_eps bash ~/.agents/skills/arduino-esp32s3-k10-xiaosense/scripts/compile-k10.sh \
  "./01_固件/K10_AI书院" COM12
```
> 必须带中文模型（`K10_MODEL=Hi_eps`），否则 `asrInit` 不完成。

## 配置
复制 `secrets.h.example` 为 `secrets.h`，填 WiFi 与电脑 IP（MQTT broker）。

## 交互
- 唤醒：**你好小行 / 你好小新**，唤醒后 12 秒内说指令
- 关键词：下一关、上一关、重播、普通话、粤语、重新开始、人脸识别、说明
- 屏幕：关卡 / 语言 / WiFi / MQTT / 最近指令
- 按键：A=下一关，B=切语言，A+B=重播
- RGB：普通话金、粤语青绿、断网暗红

## 协议
- 发布 `aotai/k10`（wake / voice_cmd / k10_status）
- 发布 `aotai/cmd`（next / prev / set_lang / goto_stage / reset）
- 订阅 `aotai/state`、`aotai/cmd`（网页操作时 K10 屏幕同步）

编译占用：Flash 26%（1.39 MB / 5 MB），RAM 17%。
