"""
Voice Command workflow — reusable Python utilities.

Import and call from agent code after transcription returns.
"""

import re

_CONTROL_CMDS = ["结束录音", "停止录音", "开始录音"]


def clean_transcript(text: str) -> str:
    """Strip control commands ('开始录音', '结束录音') from both ends."""
    for cmd in _CONTROL_CMDS:
        if text.startswith(cmd):
            text = text[len(cmd):].strip().lstrip("，。！？；、")
    for cmd in _CONTROL_CMDS:
        if text.endswith(cmd):
            text = text[: -len(cmd)].strip()
        elif text.rstrip("，。！？；、").endswith(cmd):
            text = text[: -(len(cmd) + 1)].strip()
    text = text.rstrip("，。！？；、").strip()
    return text


def format_transcript(text: str) -> str:
    """Split by punctuation marks and prefix with line numbers."""
    lines = re.split(r'(?<=[。！？；，])', text)
    lines = [l.strip() for l in lines if l.strip()]
    return "\n".join(f"{i+1}. {line}" for i, line in enumerate(lines))


def build_recording_command(source: str = "default") -> str:
    """Return the parec command string for the given audio source."""
    if source == "echo_cancel":
        return (
            "parec --device=echo_cancel_source "
            "--rate=16000 --channels=1 --format=s16le --raw "
            "> /tmp/voice_cmd.raw"
        )
    return (
        "parec --rate=16000 --channels=1 --format=s16le --raw "
        "> /tmp/voice_cmd.raw"
    )


# ffmpeg noise reduction filter string (voice-band + afftdn)
NOISE_REDUCTION_FILTER = "highpass=f=200,lowpass=f=4000,afftdn=nr=15:nf=-30"
