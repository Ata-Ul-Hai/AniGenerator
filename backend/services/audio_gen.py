"""Text-to-speech generation and audio duration measurement utilities."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import edge_tts
from gtts import gTTS
from mutagen import File as MutagenFile

logger = logging.getLogger(__name__)

DEFAULT_VOICE = "en-US-GuyNeural"


async def _synthesize_async(narration: str, output_path: str, voice: str) -> None:
    """Generate a speech audio file asynchronously with edge-tts."""

    communicator = edge_tts.Communicate(text=narration, voice=voice)
    await communicator.save(output_path)


def _read_duration_ms(audio_path: str) -> int:
    """Read audio duration in milliseconds using mutagen metadata."""

    audio = MutagenFile(audio_path)
    if audio is None or getattr(audio, "info", None) is None:
        raise ValueError(f"Unable to read duration from audio file: {audio_path}")

    length_seconds = float(audio.info.length)
    duration_ms = max(1, int(round(length_seconds * 1000)))
    return duration_ms


def _synthesize_with_gtts(narration: str, output_path: str) -> None:
    """Generate speech audio with gTTS as a fallback provider."""

    tts = gTTS(text=narration, lang="en", slow=False)
    tts.save(output_path)


def synthesize(narration: str, output_path: str) -> int:
    """Synthesize narration to an MP3 file and return duration in milliseconds."""

    if not narration.strip():
        raise ValueError("narration cannot be empty")

    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Synthesizing audio to %s", target)
    try:
        asyncio.run(_synthesize_async(narration=narration, output_path=str(target), voice=DEFAULT_VOICE))
    except Exception as exc:  # noqa: BLE001
        logger.warning("edge-tts failed; falling back to gTTS: %s", exc)
        _synthesize_with_gtts(narration=narration, output_path=str(target))

    duration_ms = _read_duration_ms(str(target))
    logger.info("Audio duration for %s is %s ms", target, duration_ms)
    return duration_ms
