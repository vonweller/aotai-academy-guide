# 02_数据 · 内容与语音

| 文件 | 说明 |
|---|---|
| content.json | 五关双语文案（zh/yue），含 2 道三选一问答 |
| map.json | 关卡坐标、行走路径、相机预设（网页与 Blender 共用） |
| audio/zh/*.mp3 | 普通话语音（zh-CN-XiaoxiaoNeural） |
| audio/yue/*.mp3 | 粤语语音（zh-HK-HiuMaanNeural） |
| audio/manifest.json | 每条音频的 id/lang/voice/text/bytes/md5 |
| tools/gen_audio.py | edge-tts 批量生成脚本 |
| data_pack/faces/ | 合成人脸样张（可打印）+ labels.json |
| 史实核对.md | 史实来源核对（content 队友整理） |

## 重新生成语音
```bash
pip install edge-tts
python tools/gen_audio.py            # 全部
python tools/gen_audio.py --lang yue --force
```
需要 ffmpeg（默认找 `D:\APP\ffmpeg-7.1-essentials_build\bin\ffmpeg.exe`，否则用 PATH 里的）。
