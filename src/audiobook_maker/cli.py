from __future__ import annotations

import argparse
from pathlib import Path

from .audio import Voice, VoiceTuning
from .pipeline import make_audiobook
from .web import run_server


DEFAULT_WORK_DIR = Path("work")
DEFAULT_VOICES = {
    "hu": Path("models/hu_HU-anna-medium.onnx"),
    "en": Path("models/en_US-lessac-medium.onnx"),
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="audiobook-maker")
    subparsers = parser.add_subparsers(dest="command", required=True)

    make = subparsers.add_parser("make", help="Convert a document to an MP3 audiobook.")
    make.add_argument("input", type=Path, help="Input .pdf, .docx, .txt, or .md file.")
    make.add_argument("--language", choices=["hu", "en"], required=True, help="Narration language.")
    make.add_argument("--voice", type=Path, help="Path to a Piper .onnx voice model.")
    make.add_argument("--output", type=Path, help="Output .mp3 path.")
    make.add_argument("--work-dir", type=Path, default=DEFAULT_WORK_DIR, help="Cache/work directory.")
    make.add_argument("--max-chars", type=int, default=1_200, help="Maximum characters per TTS chunk.")
    make.add_argument("--sentence-silence", type=float, default=0.18, help="Seconds of silence after each sentence.")
    make.add_argument("--length-scale", type=float, default=1.07, help="Speech length scale. Higher is slower.")
    make.add_argument("--noise-scale", type=float, help="Optional Piper noise scale.")
    make.add_argument("--noise-w-scale", type=float, help="Optional Piper noise width scale.")
    make.add_argument("--limit-chunks", type=int, help="Only render the first N chunks, useful for previews.")
    make.add_argument("--text-file", type=Path, help="Use this edited UTF-8 text instead of extracting the source document.")
    make.add_argument(
        "--normalizer",
        choices=["auto", "local", "nemo"],
        default="auto",
        help="Speech text normalization backend: auto, local, or strict NeMo.",
    )
    make.add_argument(
        "--preset",
        choices=["natural", "calm", "compact"],
        default="natural",
        help="Speech/prosody profile used before TTS.",
    )
    make.add_argument(
        "--link-mode",
        choices=["domain", "skip", "full"],
        default="domain",
        help="How web addresses are handled: domain, skip, or full.",
    )
    make.add_argument(
        "--no-dynamic-pauses",
        dest="dynamic_pauses",
        action="store_false",
        help="Disable structural pauses at paragraphs and clauses.",
    )
    make.add_argument(
        "--pronunciation-file",
        type=Path,
        help="UTF-8 file with source = spoken form pronunciation overrides.",
    )
    make.add_argument("--force", action="store_true", help="Regenerate all chunks.")

    ui = subparsers.add_parser("ui", help="Start the local web interface.")
    ui.add_argument("--host", default="127.0.0.1", help="UI host.")
    ui.add_argument("--port", type=int, default=8765, help="UI port.")

    args = parser.parse_args(argv)

    if args.command == "make":
        voice_path = args.voice or DEFAULT_VOICES[args.language]
        if not voice_path.exists():
            parser.error(
                f"Voice model not found: {voice_path}. "
                "Pass --voice or put the default model in the models folder."
            )
        output_path = args.output or Path("outputs") / f"{args.input.stem}-{args.language}.mp3"
        make_audiobook(
            input_path=args.input,
            output_path=output_path,
            voice=Voice(language=args.language, model=voice_path),
            work_dir=args.work_dir,
            max_chars=args.max_chars,
            tuning=VoiceTuning(
                sentence_silence=args.sentence_silence,
                length_scale=args.length_scale,
                noise_scale=args.noise_scale,
                noise_w_scale=args.noise_w_scale,
            ),
            limit_chunks=args.limit_chunks,
            source_text=args.text_file.read_text(encoding="utf-8") if args.text_file else None,
            force=args.force,
            normalizer=args.normalizer,
            preset=args.preset,
            link_mode=args.link_mode,
            dynamic_pauses=args.dynamic_pauses,
            pronunciations=(
                args.pronunciation_file.read_text(encoding="utf-8")
                if args.pronunciation_file
                else None
            ),
        )
        return 0

    if args.command == "ui":
        run_server(host=args.host, port=args.port)
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

