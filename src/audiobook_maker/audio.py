from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path


_PAUSE_MARKER_RE = re.compile(r"\[PAUSE\s*:\s*(?P<seconds>\d+(?:\.\d+)?)\s*\]", re.IGNORECASE)


@dataclass(frozen=True)
class Voice:
    language: str
    model: Path


@dataclass(frozen=True)
class VoiceTuning:
    sentence_silence: float = 0.18
    length_scale: float = 1.07
    noise_scale: float | None = None
    noise_w_scale: float | None = None


class PiperSynthesisError(RuntimeError):
    """Raised when Piper did not produce a valid audio file."""


def ensure_tools() -> None:
    missing = [tool for tool in ("piper", "ffmpeg") if _find_tool(tool) is None]
    if missing:
        raise RuntimeError(f"Missing required command(s) on PATH: {', '.join(missing)}")


def synthesize_chunk(text: str, voice: Voice, wav_path: Path, tuning: VoiceTuning) -> None:
    wav_path.parent.mkdir(parents=True, exist_ok=True)
    piper = _find_tool("piper")
    if piper is None:
        raise RuntimeError("Missing required command on PATH: piper")
    if not _PAUSE_MARKER_RE.search(text):
        _run_piper(text, voice, wav_path, tuning, piper)
        return

    try:
        with tempfile.TemporaryDirectory(prefix=f"{wav_path.stem}-", dir=wav_path.parent) as temp_dir:
            temp_root = Path(temp_dir)
            part_paths: list[Path] = []
            cursor = 0
            part_index = 0
            for match in _PAUSE_MARKER_RE.finditer(text):
                text_part = text[cursor : match.start()].strip()
                if _has_speakable_content(text_part):
                    part_path = temp_root / f"part-{part_index:03d}.wav"
                    _run_piper(text_part, voice, part_path, tuning, piper)
                    part_paths.append(part_path)
                    part_index += 1

                pause_path = temp_root / f"part-{part_index:03d}.wav"
                _write_silence(float(match.group("seconds")), pause_path)
                part_paths.append(pause_path)
                part_index += 1
                cursor = match.end()

            tail = text[cursor:].strip()
            if _has_speakable_content(tail):
                part_path = temp_root / f"part-{part_index:03d}.wav"
                _run_piper(tail, voice, part_path, tuning, piper)
                part_paths.append(part_path)

            if not part_paths:
                raise ValueError("A chunk contained a pause instruction but no audio content.")
            _concat_wavs(part_paths, wav_path)
    except (PiperSynthesisError, subprocess.CalledProcessError, OSError, ValueError):
        if wav_path.exists():
            wav_path.unlink()
        raise


def _run_piper(text: str, voice: Voice, wav_path: Path, tuning: VoiceTuning, piper: Path) -> None:
    cmd = [
        str(piper),
        "--model",
        str(voice.model),
        "--output_file",
        str(wav_path),
        "--sentence_silence",
        str(tuning.sentence_silence),
        "--length_scale",
        str(tuning.length_scale),
    ]
    if tuning.noise_scale is not None:
        cmd.extend(["--noise_scale", str(tuning.noise_scale)])
    if tuning.noise_w_scale is not None:
        cmd.extend(["--noise_w_scale", str(tuning.noise_w_scale)])
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    try:
        completed = subprocess.run(
            cmd,
            input=text,
            text=True,
            encoding="utf-8",
            env=env,
            capture_output=True,
        )
    except OSError:
        if wav_path.exists():
            wav_path.unlink()
        raise

    if completed.returncode != 0:
        if wav_path.exists():
            wav_path.unlink()
        detail = (completed.stderr or completed.stdout or "").strip()
        if len(detail) > 600:
            detail = detail[-600:]
        suffix = f": {detail}" if detail else ""
        raise PiperSynthesisError(f"Piper failed with exit code {completed.returncode}{suffix}")

    if not is_valid_wav(wav_path):
        if wav_path.exists():
            wav_path.unlink()
        raise PiperSynthesisError("Piper finished without producing a valid WAV file.")


def is_valid_wav(path: Path) -> bool:
    """Return whether *path* contains a readable, non-empty WAV stream."""
    try:
        with wave.open(str(path), "rb") as wav_file:
            return (
                wav_file.getnchannels() > 0
                and wav_file.getframerate() > 0
                and wav_file.getnframes() > 0
            )
    except (OSError, wave.Error):
        return False


def _has_speakable_content(text: str) -> bool:
    """Piper cannot synthesize punctuation-only fragments."""
    return any(character.isalnum() for character in text)


def _write_silence(seconds: float, output_path: Path) -> None:
    ffmpeg = _find_tool("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("Missing required command on PATH: ffmpeg")
    duration = max(0.05, min(seconds, 30.0))
    cmd = [
        str(ffmpeg),
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "anullsrc=r=22050:cl=mono",
        "-t",
        str(duration),
        "-c:a",
        "pcm_s16le",
        "-ar",
        "22050",
        "-ac",
        "1",
        str(output_path),
    ]
    subprocess.run(cmd, check=True)


def _concat_wavs(wav_paths: list[Path], output_path: Path) -> None:
    ffmpeg = _find_tool("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("Missing required command on PATH: ffmpeg")
    list_path = output_path.parent / f".{output_path.stem}.parts.txt"
    list_path.write_text(
        "\n".join(f"file '{_ffmpeg_path(path)}'" for path in wav_paths),
        encoding="utf-8",
    )
    cmd = [
        str(ffmpeg),
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(list_path),
        "-c:a",
        "pcm_s16le",
        "-ar",
        "22050",
        "-ac",
        "1",
        str(output_path),
    ]
    try:
        subprocess.run(cmd, check=True)
    finally:
        if list_path.exists():
            list_path.unlink()


def combine_wavs_to_mp3(wav_paths: list[Path], output_path: Path, bitrate: str = "192k") -> None:
    if not wav_paths:
        raise ValueError("No WAV chunks were generated.")

    ffmpeg = _find_tool("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("Missing required command on PATH: ffmpeg")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    list_path = output_path.with_suffix(".concat.txt")
    list_path.write_text(
        "\n".join(f"file '{_ffmpeg_path(path)}'" for path in wav_paths),
        encoding="utf-8",
    )
    cmd = [
        str(ffmpeg),
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(list_path),
        "-codec:a",
        "libmp3lame",
        "-b:a",
        bitrate,
        str(output_path),
    ]
    subprocess.run(cmd, check=True)


def chunk_hash(text: str, voice: Voice, tuning: VoiceTuning) -> str:
    payload = {
        "text": text,
        "language": voice.language,
        "model": str(voice.model.resolve()),
        "sentence_silence": tuning.sentence_silence,
        "length_scale": tuning.length_scale,
        "noise_scale": tuning.noise_scale,
        "noise_w_scale": tuning.noise_w_scale,
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _ffmpeg_path(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/").replace("'", "'\\''")


def _find_tool(name: str) -> Path | None:
    suffix = ".exe" if sys.platform == "win32" else ""
    local = Path(sys.executable).parent / f"{name}{suffix}"
    if local.exists():
        return local
    found = shutil.which(name)
    return Path(found) if found else None

