---
name: voice-command
description: 语音指令录制 → 转文字 → 确认 → 执行 的完整工作流
trigger: "语音指令 / 开始录音 / 结束录音 / voice command"
expected_requests:
  - "开始录音，我要说一段指令"
  - "结束录音，转成文字"
  - "用语音输入指令"
---

# Voice Command（语音指令工作流）

## 流程概述

```
① 用户说"开始录音"  →  后台启动录音
② 用户说话（指令内容）
③ 用户说"结束录音"  →  停止录音
④ Agent 转录音频 → 显示文字
⑤ 用户确认/修改文字
⑥ Agent 将文字作为指令执行
```

## 实现步骤

### 1. 开始录音
```bash
# 后台启动录音（16kHz, 单声道, 16-bit PCM）
parec --rate=16000 --channels=1 --format=s16le --raw > /tmp/voice_cmd.raw
```
**关键点：**
- 使用 `terminal(background=true)` 启动
- 记录 `session_id` 以便后续停止
- 音频格式：**16kHz / mono / s16le**（与 FunASR 要求一致）

### 2. 结束录音
```bash
# 1. 停止录音进程
process(action="kill", session_id="<记录的 session_id>")

# 2. 原始 PCM 转 WAV（语音频带过滤 + 强力降噪，实战验证有效）
#    highpass=200Hz + lowpass=4000Hz 切割人声频带
#    afftdn nr=15:nf=-30 强力降噪
#    注意：此参数在背景有清晰人声播放时仍有效
ffmpeg -f s16le -ar 16000 -ac 1 -i /tmp/voice_cmd.raw \
       -af "highpass=f=200,lowpass=f=4000,afftdn=nr=15:nf=-30" \
       -y /tmp/voice_cmd.wav
```
也可用 `scripts/voice_cmd_pipeline.sh` 一键执行。

### 3. 转录音频 → 文本
```bash
# 发送到 FunASR daemon
echo '{"action":"transcribe","file_path":"/tmp/voice_cmd.wav"}' | nc -U -w 30 ~/.hermes/run/funasrd.sock
```
返回示例：
```json
{"success": true, "transcript": "今天天气真不错，我们去散步吧。", "elapsed": 0.312}
```

### 4. 清洗转录文本 + 格式化显示 + 确认

**自动清洗：** 录音结尾的控制指令（如"结束录音"）自动去掉，不作为指令内容。

```python
import re

# 控制指令列表（录音末尾可能混入的）
_CONTROL_CMDS = ["结束录音", "停止录音", "开始录音"]

def clean_transcript(text: str) -> str:
    \"\"\"去掉录音开头和末尾混入的控制指令\"\"\"
    # 去掉开头的控制指令（如"开始录音。作为学生…"）
    for cmd in _CONTROL_CMDS:
        if text.startswith(cmd):
            text = text[len(cmd):].strip().lstrip("，。！？；、")
    # 去掉末尾的控制指令（如"…结束录音。"）
    for cmd in _CONTROL_CMDS:
        if text.endswith(cmd):
            text = text[: -len(cmd)].strip()
        elif text.rstrip("，。！？；、").endswith(cmd):
            text = text[: -(len(cmd) + 1)].strip()
    text = text.rstrip("，。！？；、").strip()
    return text

def format_transcript(text: str) -> str:
    \"\"\"按标点符号分行加行号显示转录结果\"\"\"
    lines = re.split(r'(?<=[。！？；，])', text)
    lines = [l.strip() for l in lines if l.strip()]
    return "\n".join(f"{i+1}. {line}" for i, line in enumerate(lines))
```

示例显示效果：
```
转录结果：
1. 今天天气真不错，
2. 适合出去散步，
3. 你觉得如何？

需要修改吗？（回复修改内容，或回复"没问题"执行）
```

### 5. 执行指令
- 用户说"没问题" → 将文字作为指令执行
- 用户说"把散步改成打球" → 修改后再次确认

## 注意事项

### 参考文件

- `references/workflow.py` — 可复用的 Python 函数：clean_transcript, format_transcript, build_recording_commands
- `references/noise-reduction.md` — 分层噪音抑制方案（afftdn / 降增益 / WebRTC / 回声消除）

### 录音文件清理
每次录音开始前，清除上次残留：
```bash
rm -f /tmp/voice_cmd.raw /tmp/voice_cmd.wav
```

### daemon 异常处理
如果转录失败（`success: false`），备选方案：
1. 检查 daemon 是否运行：`ls ~/.hermes/run/funasrd.sock && echo "alive"`
2. 重启 daemon（见 `audio-recording-and-stt` 技能）
3. 告知用户 daemon 异常，建议用 Ctrl+B 直接录音

### 音频格式必须严格匹配
FunASR daemon 要求：**16000Hz, mono, s16le PCM**。用 parec 参数保证一致性。

### 超时控制
- 录音超时：`max_recording_seconds: 120`（配置在 Hermes config）
- 转录超时：nc 的 `-w 30`（30 秒，模型推理一般 <1s）
- 用户确认超时：无限等待（用户决定确认时间）

## 用户风格偏好

- **要求严谨：** 用户接受真实环境测试，不接受"忽略背景噪音就行"。必须确保方案在背景有播放音频时仍有效。
- **先报结果再执行：** 转录结果必须先用 `format_transcript` 分行加行号展示，经用户确认后再执行。
- **持续迭代：** 用户会给反馈——如果不理想会说明具体问题（如没标点、背景噪音残留等）。耐心测试，每轮只改一个变量。

## 已知问题 & 规避

### 背景噪音干扰（最常见）
如果用户附近有音响/电视/教学音频正在播放，麦克风会一并录制并转录为文本。
- **现象：** 转录结果以无关内容为主，用户指令被淹没
- **分级应对策略：**

**轻度噪音**（风扇、空调、环境底噪）→ `afftdn` 降噪滤镜
```bash
ffmpeg -f s16le -ar 16000 -ac 1 -i /tmp/voice_cmd.raw \
       -af "afftdn=nf=-25" -y /tmp/voice_cmd.wav
```

**中度噪音**（近距离人声播放、电视声、音箱声）→ 降麦克风增益 + 降噪
```bash
# 录音前降低麦克风增益（压低远处声音）
pactl set-source-volume alsa_input.pci-0000_00_1f.3.analog-stereo 40%
# 录音完成后恢复
pactl set-source-volume alsa_input.pci-0000_00_1f.3.analog-stereo 61%
# 转 WAV 时加降噪
ffmpeg -f s16le -ar 16000 -ac 1 -i /tmp/voice_cmd.raw \
       -af "afftdn=nf=-25" -y /tmp/voice_cmd.wav
```

**重度噪音**（大声播放、两人同时说话）→ WebRTC 实时降噪
```bash
# 1. 加载 WebRTC 噪声抑制模块
pactl load-module module-echo-cancel \
  source_name=noise_cancel_source \
  aec_method=webrtc \
  aec_args="analog_gain_control=0 digital_gain_control=1 noise_suppression=1"

# 2. 从降噪后的虚拟源录音
parec --device=noise_cancel_source --rate=16000 --channels=1 \
      --format=s16le --raw > /tmp/voice_cmd.raw

# 3. 结束后卸载模块（记下 load-module 返回的 ID）
pactl unload-module <module_id>
```

**理论极限提示：** 所有数字降噪对**同类型信号**（另一个人声播放源）效果有限。最佳方案始终是物理层——录音前关闭或静音附近播放设备。

### 控制指令识别失真
"结束录音"四个字可能被 ASR 识别为形近词或乱码（如"结说你""结束你"等）。
- **现象：** `clean_transcript` 无法匹配到精确的控制指令，末尾残留乱码
- **规避：** 显示结果后请用户确认，人工删掉乱码部分即可

### 重录流程
当前次录音效果不理想时，简单三步重来：
1. 用户说"忽略内容" → 作废当前转录
2. Agent 清理录音文件
3. 用户说"开始录音" → 开始新一轮
