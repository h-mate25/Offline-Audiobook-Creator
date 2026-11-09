from __future__ import annotations

import logging
import re
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .text import clean_text


_PAUSE_MARKER_RE = re.compile(
    r"\[PAUSE\s*:\s*(?P<seconds>\d+(?:\.\d+)?)\s*\]",
    re.IGNORECASE,
)
_NEMO_NORMALIZERS: dict[tuple[str, str], Any] = {}


class NormalizationError(RuntimeError):
    """Raised when the explicitly requested normalizer cannot run."""


@dataclass(frozen=True)
class NormalizationResult:
    chunks: list[str]
    backend: str
    warning: str = ""


def nemo_status() -> dict[str, object]:
    """Return a small, UI-safe status report without initializing a grammar."""
    try:
        _load_nemo_class()
    except Exception as exc:  # NeMo can fail while importing Pynini.
        return {
            "available": False,
            "name": "NeMo Text Processing",
            "reason": _short_exception(exc),
        }
    return {
        "available": True,
        "name": "NeMo Text Processing",
        "reason": "A NeMo normalizer elérhető ebben a Python-környezetben.",
    }


def normalize_chunks(
    chunks: list[str],
    language: str,
    mode: str = "auto",
    cache_dir: Path | None = None,
) -> NormalizationResult:
    """Normalize text for speech while preserving manual pause markers.

    ``auto`` prefers NeMo when the optional dependency is usable and otherwise
    returns the already-cleaned local text. ``local`` never imports NeMo.
    ``nemo`` is strict and raises a useful error when the optional stack is not
    available.
    """
    if mode not in {"auto", "local", "nemo"}:
        raise ValueError(f"Unknown text normalizer mode: {mode}")

    cleaned_chunks = [clean_text(chunk) for chunk in chunks]
    if mode == "local":
        return NormalizationResult(cleaned_chunks, backend="local")

    status = nemo_status()
    if not status["available"]:
        if mode == "nemo":
            raise NormalizationError(
                "A NeMo Text Processing nem indítható ebben a környezetben. "
                f"Részlet: {status['reason']}"
            )
        return NormalizationResult(
            cleaned_chunks,
            backend="local-fallback",
            warning=f"NeMo nem érhető el, ezért helyi tisztítás fut. {status['reason']}",
        )

    try:
        normalizer = _get_nemo_normalizer(language, cache_dir)
        normalized = [_normalize_chunk_with_nemo(chunk, normalizer) for chunk in cleaned_chunks]
    except Exception as exc:
        if mode == "nemo":
            raise NormalizationError(f"NeMo normalizálási hiba: {_short_exception(exc)}") from exc
        return NormalizationResult(
            cleaned_chunks,
            backend="local-fallback",
            warning=f"NeMo hibába ütközött, ezért helyi tisztítás fut. {_short_exception(exc)}",
        )

    return NormalizationResult(normalized, backend="nemo")


def _load_nemo_class() -> Any:
    from nemo_text_processing.text_normalization.normalize import Normalizer

    return Normalizer


def _get_nemo_normalizer(language: str, cache_dir: Path | None) -> Any:
    if language not in {"hu", "en"}:
        raise NormalizationError(f"A NeMo normalizáló nyelve nem támogatott: {language}")

    resolved_cache = str(cache_dir.resolve()) if cache_dir else ""
    key = (language, resolved_cache)
    if key in _NEMO_NORMALIZERS:
        return _NEMO_NORMALIZERS[key]

    if cache_dir:
        cache_dir.mkdir(parents=True, exist_ok=True)

    normalizer_class = _load_nemo_class()
    # NeMo emits INFO messages while it creates its finite-state grammar
    # cache.  Keep that implementation detail out of the audiobook UI log.
    with _quiet_nemo_logging():
        normalizer = normalizer_class(
            input_case="cased",
            lang=language,
            deterministic=True,
            cache_dir=resolved_cache or None,
            overwrite_cache=False,
            post_process=True,
        )
    _NEMO_NORMALIZERS[key] = normalizer
    return normalizer


def _normalize_chunk_with_nemo(chunk: str, normalizer: Any) -> str:
    """Normalize speech fragments separately so editor pause markers survive."""
    pieces: list[str] = []
    cursor = 0
    for match in _PAUSE_MARKER_RE.finditer(chunk):
        pieces.append(_normalize_fragment(chunk[cursor : match.start()], normalizer))
        pieces.append(match.group(0))
        cursor = match.end()
    pieces.append(_normalize_fragment(chunk[cursor:], normalizer))
    return _tidy_normalized_text("".join(pieces))


def _normalize_fragment(fragment: str, normalizer: Any) -> str:
    if not fragment.strip() or not any(character.isalnum() for character in fragment):
        return fragment
    with _quiet_nemo_logging():
        return normalizer.normalize(
            fragment,
            verbose=False,
            punct_pre_process=True,
            punct_post_process=True,
        )


@contextmanager
def _quiet_nemo_logging():
    previous_disable_level = logging.root.manager.disable
    logging.disable(logging.INFO)
    try:
        yield
    finally:
        logging.disable(previous_disable_level)


def _tidy_normalized_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _short_exception(exc: Exception) -> str:
    detail = str(exc).strip().replace("\r", " ").replace("\n", " ")
    if len(detail) > 240:
        detail = detail[:237] + "..."
    return detail or type(exc).__name__

