# Noise Reduction Strategies for Voice Commands

实战验证有效，按干扰程度从轻到重排列。

---

## Level 1: 轻度噪音（风扇、空调、环境底噪）

单独的 `afftdn` 即可。无需调整麦克风增益。

```bash
ffmpeg -f s16le -ar 16000 -ac 1 -i /tmp/voice_cmd.raw \
       -af "afftdn=nf=-25" -y /tmp/voice_cmd.wav
```

**参数说明：** `nf=-25` 表示噪底阈值（-25dBFS），低于此的音量视为噪声压掉。

---

## Level 2: 中度噪音（音箱/电视声、近距离人声播放）

语音频带切割 + 强力降噪。**这是最常用的方案，实战验证有效。**

```bash
ffmpeg -f s16le -ar 16000 -ac 1 -i /tmp/voice_cmd.raw \
       -af "highpass=f=200,lowpass=f=4000,afftdn=nr=15:nf=-30" \
       -y /tmp/voice_cmd.wav
```

**参数说明：**
- `highpass=f=200` — 滤除 200Hz 以下低频（空调嗡鸣、建筑震动）
- `lowpass=f=4000` — 滤除 4000Hz 以上高频（电子噪音、嘶嘶声）
- `afftdn=nr=15:nf=-30` — 频域降噪，nr=15 降噪强度，nf=-30 噪底阈值

**验证结果：** 背景有教学音频播放时，此参数成功滤掉背景，只保留用户人声。

---

## Level 3: 重度噪音 + 降低麦克风增益

先物理压低增益，再数字降噪。适合背景音比用户声音还大的情况。

```bash
# 1. 录音前降低增益到 40%
pactl set-source-volume alsa_input.pci-0000_00_1f.3.analog-stereo 40%

# 2. 录音（声音小但干净）
parec --rate=16000 --channels=1 --format=s16le --raw > /tmp/voice_cmd.raw

# 3. 转 WAV 时降噪
ffmpeg -f s16le -ar 16000 -ac 1 -i /tmp/voice_cmd.raw \
       -af "highpass=f=200,lowpass=f=4000,afftdn=nr=15:nf=-30" \
       -y /tmp/voice_cmd.wav

# 4. 录音完成后恢复增益
pactl set-source-volume alsa_input.pci-0000_00_1f.3.analog-stereo 61%
```

**注意：** 增益太低会导致用户声音也变小，可能转录失败。建议从 50% 开始试。

---

## Level 4: WebRTC 实时降噪（PulseAudio 模块）

PulseAudio 的 `module-echo-cancel` 内建 WebRTC 噪声抑制，实时过滤。

```bash
# 1. 加载模块，记下返回的 ID
pactl load-module module-echo-cancel \
  source_name=noise_cancel_source \
  aec_method=webrtc \
  aec_args="analog_gain_control=0 digital_gain_control=1 noise_suppression=1"

# 2. 从降噪后的虚拟源录音
parec --device=noise_cancel_source --rate=16000 \
      --channels=1 --format=s16le --raw > /tmp/voice_cmd.raw

# 3. 结束后卸载模块
pactl unload-module <module_id>

# 4. 降噪源录音的 WAV 转换不再需要 ffmpeg 降噪滤镜
ffmpeg -f s16le -ar 16000 -ac 1 -i /tmp/voice_cmd.raw -y /tmp/voice_cmd.wav
```

**适用场景：** 持续的背景噪音（风扇、马路噪音、多人环境）

---

## Level 5: WebRTC 回声消除（指定麦克风+喇叭设备）

专门解决 **喇叭播放的音频被麦克风重新拾取** 的问题（回声）。

```bash
pactl load-module module-echo-cancel \
  source_name=echo_cancel_source \
  sink_name=echo_cancel_sink \
  aec_method=webrtc \
  source_master=alsa_input.pci-0000_00_1f.3.analog-stereo \
  sink_master=alsa_output.pci-0000_00_1f.3.analog-stereo \
  aec_args="analog_gain_control=0 digital_gain_control=1 noise_suppression=1"
```

**注意：** 回声消除仅对 **同一台电脑** 的喇叭→麦克风回路有效。如果背景音来自外部设备（手机、电视），回声消除无效，退回到 Level 2-3 方案。

---

## 物理层方案（最有效）

所有数字降噪都有理论极限——遇到同类型信号（另一个清晰人声），算法很难区分。最佳方案：

1. **关掉或静音附近播放设备**
2. **麦克风贴近嘴边**
3. **说话时口齿清晰、音量适中**
