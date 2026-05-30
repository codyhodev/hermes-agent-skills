---
name: audio-recording-and-stt
description: 录音转文字全流程 — 录制音频 → STT 语音识别 → 输出文本
trigger: "录音 / 语音识别 / 转文字 / STT / 语音输入"
expected_requests:
  - "怎么录音转文字"
  - "帮我录一段话"
  - "语音识别怎么用"
  - "测试录音效果"
---

# Audio Recording & STT（录音转文字）

## 录音方式

### 方式一：Hermes TUI 内置录音（推荐）
按 **Ctrl+B** 开始录音 → 说话 → 再次按 **Ctrl+B**（或静音自动停止）→ 自动识别出文本

- 录音配置见 `~/.hermes/config.yaml` 的 `voice` 段
- 录音保存在 `~/.hermes/audio_cache/`
- 默认静音停顿时长：**3秒**（`silence_duration: 3.0`）

### 方式二：终端命令行录音（带降噪）
```bash
# 用 parec + ffmpeg 录制 + 降噪
parec --rate=16000 --channels=1 --format=s16le --raw > /tmp/voice_cmd.raw
ffmpeg -f s16le -ar 16000 -ac 1 -i /tmp/voice_cmd.raw \
       -af "highpass=f=200,lowpass=f=4000,afftdn=nr=15:nf=-30" \
       -y /tmp/voice_cmd.wav
```
**降噪说明：** `highpass=f=200` 滤除低频（空调/风扇），`lowpass=f=4000` 滤除高频（嘶嘶声/电子噪），`afftdn=nr=15:nf=-30` 频域自适应降噪。实战验证此参数在背景有清晰人声播放时仍能有效保留用户语音。
四个级别的降噪方案见 `voice-command` 技能中的 `references/noise-reduction.md`。

### 方式三：语音指令工作流（录音→转文字→确认→执行）
**见 `voice-command` 技能**，实现完整的"开始录音→说指令→结束录音→展示→确认→执行"闭环。
包含：
- 自动清洗（去掉"开始录音""结束录音"等控制指令）
- 标点分行加行号展示（`format_transcript`）
- 多级降噪方案（`references/noise-reduction.md`）

```python
# 核心函数可复用
from references.workflow import clean_transcript, format_transcript

raw = "今天天气真不错，适合出去散步，你觉得如何？结束录音。"
cleaned = clean_transcript(raw)        # → "今天天气真不错，适合出去散步，你觉得如何？"
formatted = format_transcript(cleaned)  # → "1. 今天天气真不错，\n2. 适合出去散步，\n3. 你觉得如何？"
```

## STT 配置

当前 STT 配置（`~/.hermes/config.yaml`）：
```yaml
stt:
  enabled: true
  provider: funasr          # STT 引擎
voice:
  record_key: ctrl+b         # 录音快捷键
  max_recording_seconds: 120 # 最长录音 2 分钟
  silence_threshold: 200     # 静音阈值
  silence_duration: 3.0      # 静音多久自动停止（秒）
```

## FunASR 插件（当前使用的 STT 引擎）

- **项目：** `git@github.com:codyhodev/funasr-hermes-plugin.git`
- **Daemon：** 运行在后台（PID 文件 `~/.hermes/run/funasrd.pid`）
- **Socket：** `~/.hermes/run/funasrd.sock`
- **加载的模型（按加载顺序）：**
  - `SenseVoiceSmall` — 语音识别，输出纯文本（无标点）
  - `iic/punc_ct-transformer_zh-cn-common-vocab272727-pytorch` — 标点恢复模型，**基于语义**添加逗号句号

> **为什么用 ct-punc 而非 VAD？** 旧方案通过 silero-vad 检测音频停顿时长来猜标点位置（<0.15s=无标点，0.15~0.4s=逗号，≥0.4s=句号），但用户正常语速下停顿往往不够长，导致标点缺失。ct-punc 是 FunASR 官方的标点恢复模型，理解句子语义后加标点，**不依赖停顿时长**，准确率高得多。

### 查看 daemon 状态
```bash
# 检查是否在运行
ls ~/.hermes/run/funasrd.sock && echo "Daemon OK" || echo "Daemon not running"
cat ~/.hermes/run/funasrd.pid

# Ping 测试
echo '{"action":"ping"}' | nc -U -w 3 ~/.hermes/run/funasrd.sock
```

### 重启 daemon
```bash
# 停掉旧的
kill $(cat ~/.hermes/run/funasrd.pid)
rm -f ~/.hermes/run/funasrd.sock ~/.hermes/run/funasrd.pid ~/.hermes/run/funasrd.refcount

# 启动新的（用 Hermes venv 的 Python）
~/.hermes/hermes-agent/venv/bin/python3 ~/.hermes/plugins/funasr/funasrd.py &
```

### 手动测试识别
```bash
# 找一个 WAV 文件发到 daemon 测试
echo '{"action":"transcribe","file_path":"/tmp/test.wav"}' | nc -U -w 30 ~/.hermes/run/funasrd.sock
```

## 故障排查

| 现象 | 原因 | 解决 |
|------|------|------|
| 录音没反应 | 麦克风权限/设备问题 | 检查 `pactl list sources short` |
| 识别无标点 | daemon 未加载 ct-punc | 重启 daemon |
| 识别结果空白 | 音频质量差/太短 | 用 `parec` 手动录一段测试 |
| 识别结果混入无关内容 | 环境噪音（音箱/电视/教学音频） | 录音前关闭附近扬声器 |
| 控制指令被识别为乱码 | ASR 对"结束录音"识别失真 | 用 `clean_transcript` 函数自动清洗（见 `voice-command` 技能），人工协助确认 |

## 音频要求

- **格式：** WAV（PCM）
- **采样率：** 16000 Hz（16kHz）
- **声道：** 单声道（mono）
- **位深：** 16-bit signed int
