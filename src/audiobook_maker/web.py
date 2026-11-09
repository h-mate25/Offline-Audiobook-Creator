from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import threading
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Annotated

import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .document import read_document
from .normalization import nemo_status
from .text import chunk_text, clean_text


APP_ROOT = Path.cwd()
PACKAGE_ROOT = Path(__file__).resolve().parent
STATIC_ROOT = PACKAGE_ROOT / "static"
MODELS_DIR = APP_ROOT / "models"
INPUTS_DIR = APP_ROOT / "inputs"
OUTPUTS_DIR = APP_ROOT / "outputs"
WORK_UI_DIR = APP_ROOT / "work-ui"

_JOB_RE = re.compile(r"\[(\d+)/(\d+)\]\s+(.+)")
_CHUNKS_RE = re.compile(r"Chunks:\s+(\d+)")
_FILENAME_RE = re.compile(r"[^A-Za-z0-9._ -]+")
_JOBS_LOCK = threading.Lock()
_JOBS: dict[str, "Job"] = {}


@dataclass
class Job:
    id: str
    status: str
    input_name: str
    output_path: str
    command: list[str]
    current: int = 0
    total: int = 0
    message: str = ""
    error: str = ""
    logs: list[str] = field(default_factory=list)


app = FastAPI(title="Offline Audiobook Maker")
app.mount("/static", StaticFiles(directory=STATIC_ROOT), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_ROOT / "index.html")


@app.get("/api/settings")
def settings() -> dict[str, object]:
    return {
        "cwd": str(APP_ROOT),
        "voices": _list_voices(),
        "defaults": {
            "hu": "models/hu_HU-anna-medium.onnx",
            "en": "models/en_US-lessac-medium.onnx",
            "sentenceSilence": 0.18,
            "lengthScale": 1.07,
            "maxChars": 1200,
            "previewChunks": 2,
            "preset": "natural",
            "linkMode": "domain",
            "dynamicPauses": True,
        },
        "normalization": nemo_status(),
    }


@app.post("/api/preview")
def preview_text(
    source_mode: Annotated[str, Form()],
    local_path: Annotated[str, Form()] = "",
    file: Annotated[UploadFile | None, File()] = None,
) -> dict[str, object]:
    input_path = _resolve_input(source_mode, local_path, file)
    try:
        text = clean_text(read_document(input_path))
        chunks = chunk_text(text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "sourcePath": str(input_path),
        "inputName": input_path.name,
        "text": text,
        "characters": len(text),
        "chunks": len(chunks),
    }


@app.post("/api/jobs")
def create_job(
    language: Annotated[str, Form()],
    voice: Annotated[str, Form()],
    source_mode: Annotated[str, Form()],
    local_path: Annotated[str, Form()] = "",
    output_name: Annotated[str, Form()] = "",
    max_chars: Annotated[int, Form()] = 1200,
    sentence_silence: Annotated[float, Form()] = 0.18,
    length_scale: Annotated[float, Form()] = 1.07,
    noise_scale: Annotated[str, Form()] = "",
    noise_w_scale: Annotated[str, Form()] = "",
    preview_chunks: Annotated[int, Form()] = 2,
    job_type: Annotated[str, Form()] = "full",
    normalizer: Annotated[str, Form()] = "auto",
    preset: Annotated[str, Form()] = "natural",
    link_mode: Annotated[str, Form()] = "domain",
    dynamic_pauses: Annotated[bool, Form()] = True,
    pronunciations: Annotated[str, Form()] = "",
    force: Annotated[bool, Form()] = False,
    edited_text: Annotated[str, Form()] = "",
    file: Annotated[UploadFile | None, File()] = None,
) -> dict[str, str]:
    if language not in {"hu", "en"}:
        raise HTTPException(status_code=400, detail="Unsupported language.")
    if normalizer not in {"auto", "local", "nemo"}:
        raise HTTPException(status_code=400, detail="Unsupported text normalizer.")
    if preset not in {"natural", "calm", "compact"}:
        raise HTTPException(status_code=400, detail="Unsupported speech preset.")
    if link_mode not in {"domain", "skip", "full"}:
        raise HTTPException(status_code=400, detail="Unsupported web address mode.")

    input_path = _resolve_input(source_mode, local_path, file)
    voice_path = _resolve_voice(voice)
    audio_preview = job_type in {"audio-preview", "voice-test"}
    preview = audio_preview
    output_path = _output_path(input_path, language, output_name, preview)
    job_id = uuid.uuid4().hex

    args = [
        sys.executable,
        "-m",
        "audiobook_maker.cli",
        "make",
        str(input_path),
        "--language",
        language,
        "--voice",
        str(voice_path),
        "--output",
        str(output_path),
        "--work-dir",
        str(WORK_UI_DIR),
        "--max-chars",
        str(max_chars),
        "--sentence-silence",
        str(sentence_silence),
        "--length-scale",
        str(length_scale),
    ]
    edited_path: Path | None = None
    if edited_text.strip():
        WORK_UI_DIR.mkdir(parents=True, exist_ok=True)
        edited_path = WORK_UI_DIR / f"{job_id}-edited.txt"
        edited_path.write_text(edited_text, encoding="utf-8")
        args.extend(["--text-file", str(edited_path)])
    if pronunciations.strip():
        WORK_UI_DIR.mkdir(parents=True, exist_ok=True)
        pronunciation_path = WORK_UI_DIR / f"{job_id}-pronunciations.txt"
        pronunciation_path.write_text(pronunciations, encoding="utf-8")
        args.extend(["--pronunciation-file", str(pronunciation_path)])
    if noise_scale.strip():
        args.extend(["--noise-scale", noise_scale.strip()])
    if noise_w_scale.strip():
        args.extend(["--noise-w-scale", noise_w_scale.strip()])
    if audio_preview:
        args.extend(["--limit-chunks", str(max(1, preview_chunks))])
    args.extend(["--normalizer", normalizer])
    args.extend(["--preset", preset, "--link-mode", link_mode])
    if not dynamic_pauses:
        args.append("--no-dynamic-pauses")
    if force:
        args.append("--force")

    job = Job(
        id=job_id,
        status="queued",
        input_name=input_path.name,
        output_path=str(output_path),
        command=args,
    )
    with _JOBS_LOCK:
        _JOBS[job_id] = job

    thread = threading.Thread(target=_run_job, args=(job_id,), daemon=True)
    thread.start()
    return {"jobId": job_id}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, object]:
    job = _get_job(job_id)
    data = asdict(job)
    data["downloadReady"] = job.status == "done" and Path(job.output_path).exists()
    return data


@app.get("/api/jobs/{job_id}/download")
def download(job_id: str) -> FileResponse:
    job = _get_job(job_id)
    path = Path(job.output_path)
    if job.status != "done" or not path.exists():
        raise HTTPException(status_code=404, detail="Output is not ready yet.")
    return FileResponse(path, filename=path.name, media_type="audio/mpeg")


def run_server(host: str = "127.0.0.1", port: int = 8765) -> None:
    print(f"Open UI: http://{host}:{port}", flush=True)
    uvicorn.run(app, host=host, port=port, log_level="warning")


def main() -> None:
    run_server()


def _run_job(job_id: str) -> None:
    job = _get_job(job_id)
    _update_job(job_id, status="running", message="Starting conversion...")
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"

    try:
        process = subprocess.Popen(
            job.command,
            cwd=APP_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            env=env,
        )
    except OSError as exc:
        _update_job(job_id, status="failed", error=str(exc), message="Could not start conversion.")
        return

    assert process.stdout is not None
    for raw_line in process.stdout:
        line = raw_line.rstrip()
        _append_log(job_id, line)
        _parse_progress(job_id, line)

    code = process.wait()
    if code == 0:
        _update_job(job_id, status="done", message="Done.")
    else:
        _update_job(job_id, status="failed", error=f"Conversion failed with exit code {code}.")


def _parse_progress(job_id: str, line: str) -> None:
    chunk_match = _CHUNKS_RE.search(line)
    if chunk_match:
        _update_job(job_id, total=int(chunk_match.group(1)))
        return

    job_match = _JOB_RE.search(line)
    if job_match:
        current = int(job_match.group(1))
        total = int(job_match.group(2))
        message = job_match.group(3)
        _update_job(job_id, current=current, total=total, message=message)
        return

    if line.startswith("Combining MP3"):
        _update_job(job_id, message="Combining MP3...")
    elif line.startswith("Done:"):
        _update_job(job_id, message=line)


def _get_job(job_id: str) -> Job:
    with _JOBS_LOCK:
        job = _JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Unknown job.")
    return job


def _update_job(job_id: str, **changes: object) -> None:
    with _JOBS_LOCK:
        job = _JOBS[job_id]
        for key, value in changes.items():
            setattr(job, key, value)


def _append_log(job_id: str, line: str) -> None:
    with _JOBS_LOCK:
        job = _JOBS[job_id]
        job.logs.append(line)
        job.logs = job.logs[-250:]


def _resolve_input(source_mode: str, local_path: str, upload: UploadFile | None) -> Path:
    if source_mode == "path":
        raw = local_path.strip().strip('"')
        if not raw:
            raise HTTPException(status_code=400, detail="Local path is empty.")
        path = Path(raw).expanduser()
        if not path.exists():
            raise HTTPException(status_code=400, detail=f"Input file does not exist: {path}")
        return path

    if upload is None or not upload.filename:
        raise HTTPException(status_code=400, detail="No file was uploaded.")
    INPUTS_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = _safe_filename(upload.filename)
    path = INPUTS_DIR / f"{uuid.uuid4().hex[:8]}-{safe_name}"
    with path.open("wb") as target:
        shutil.copyfileobj(upload.file, target)
    return path


def _resolve_voice(value: str) -> Path:
    raw = value.strip().strip('"')
    if not raw:
        raise HTTPException(status_code=400, detail="Voice model is empty.")
    path = Path(raw)
    if not path.is_absolute():
        path = APP_ROOT / path
    if not path.exists():
        raise HTTPException(status_code=400, detail=f"Voice model does not exist: {path}")
    return path


def _output_path(input_path: Path, language: str, output_name: str, preview: bool) -> Path:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    if output_name.strip():
        name = _safe_filename(output_name.strip())
        if preview:
            output_stem = Path(name).stem
            output_suffix = Path(name).suffix or ".mp3"
            name = f"{output_stem}-preview{output_suffix}"
    else:
        suffix = f"{language}-preview" if preview else f"{language}-custom"
        name = f"{input_path.stem}-{suffix}.mp3"
    if not name.lower().endswith(".mp3"):
        name += ".mp3"
    return OUTPUTS_DIR / name


def _safe_filename(name: str) -> str:
    safe = Path(name).name.strip().replace("\0", "")
    safe = _FILENAME_RE.sub("_", safe)
    safe = safe.strip(" .")
    return safe or f"output-{uuid.uuid4().hex[:8]}.mp3"


def _list_voices() -> list[dict[str, str]]:
    if not MODELS_DIR.exists():
        return []
    voices = []
    for model in sorted(MODELS_DIR.glob("*.onnx")):
        voices.append(
            {
                "name": model.stem,
                "path": str(model.relative_to(APP_ROOT)),
                "language": _guess_language(model.name),
            }
        )
    return voices


def _guess_language(name: str) -> str:
    lowered = name.lower()
    if lowered.startswith("hu_"):
        return "hu"
    if lowered.startswith("en_"):
        return "en"
    return ""

