from __future__ import annotations

import json
from pathlib import Path

from .audio import Voice, VoiceTuning, chunk_hash, combine_wavs_to_mp3, ensure_tools, is_valid_wav, synthesize_chunk
from .document import read_document
from .normalization import normalize_chunks
from .text import (
    SpeechTextOptions,
    chunk_text,
    get_prosody_profile,
    parse_pronunciation_map,
    prepare_speech_text,
)


def make_audiobook(
    input_path: Path,
    output_path: Path,
    voice: Voice,
    work_dir: Path,
    max_chars: int = 1_200,
    tuning: VoiceTuning = VoiceTuning(),
    limit_chunks: int | None = None,
    source_text: str | None = None,
    force: bool = False,
    normalizer: str = "auto",
    preset: str = "natural",
    link_mode: str = "domain",
    dynamic_pauses: bool = True,
    pronunciations: str | None = None,
) -> None:
    ensure_tools()

    text = source_text if source_text is not None else read_document(input_path)
    profile = get_prosody_profile(preset)
    speech_text = prepare_speech_text(
        text,
        language=voice.language,
        options=SpeechTextOptions(
            link_mode=link_mode,
            dynamic_pauses=dynamic_pauses,
            paragraph_pause=profile.paragraph_pause,
            clause_pause=profile.clause_pause,
            pronunciation_map=parse_pronunciation_map(pronunciations),
        ),
    )
    chunks = chunk_text(speech_text, max_chars=max_chars)
    if limit_chunks is not None:
        chunks = chunks[:limit_chunks]
    if not chunks:
        raise ValueError("No readable text chunks were produced.")

    normalization = normalize_chunks(
        chunks,
        language=voice.language,
        mode=normalizer,
        cache_dir=work_dir / "nemo-cache" / voice.language,
    )
    chunks = normalization.chunks

    job_dir = work_dir / input_path.stem
    text_dir = job_dir / "text"
    wav_dir = job_dir / "wav"
    manifest_path = job_dir / "manifest.json"
    text_dir.mkdir(parents=True, exist_ok=True)
    wav_dir.mkdir(parents=True, exist_ok=True)

    manifest = _load_manifest(manifest_path)
    wav_paths: list[Path] = []
    next_manifest: dict[str, dict[str, str]] = {}

    print(f"Input: {input_path}", flush=True)
    print(f"Chunks: {len(chunks)}", flush=True)
    print(f"Text normalizer: {normalization.backend}", flush=True)
    if normalization.warning:
        print(f"Text normalizer note: {normalization.warning}", flush=True)

    for index, chunk in enumerate(chunks, start=1):
        key = f"{index:05d}"
        text_path = text_dir / f"{key}.txt"
        wav_path = wav_dir / f"{key}.wav"
        digest = chunk_hash(chunk, voice, tuning)
        next_manifest[key] = {"hash": digest, "wav": str(wav_path)}

        text_path.write_text(chunk, encoding="utf-8")
        cached = (
            manifest.get(key, {}).get("hash") == digest
            and wav_path.exists()
            and is_valid_wav(wav_path)
        )
        if cached and not force:
            print(f"[{index}/{len(chunks)}] cached", flush=True)
        else:
            print(f"[{index}/{len(chunks)}] synthesizing", flush=True)
            synthesize_chunk(chunk, voice, wav_path, tuning)
        wav_paths.append(wav_path)

    manifest_path.write_text(json.dumps(next_manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Combining MP3...", flush=True)
    combine_wavs_to_mp3(wav_paths, output_path)
    print(f"Done: {output_path}", flush=True)


def _load_manifest(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if isinstance(data, dict):
        return data
    return {}

