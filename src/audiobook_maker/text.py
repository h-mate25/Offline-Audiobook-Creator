from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Mapping
from urllib.parse import urlsplit


_MULTISPACE_RE = re.compile(r"[ \t]+")
_BLANK_LINES_RE = re.compile(r"\n{3,}")
_NUMERIC_INTERNAL_DOT_RE = re.compile(r"(?<=\d)\.(?=\d|\s+[a-záéíóöőúüű])")
_HYPHEN_LINEBREAK_RE = re.compile(r"(\w)-\n(\w)")
_SOFT_LINEBREAK_RE = re.compile(r"(?<![\n.!?;:])\n(?!\n)")
_SENTENCE_END_RE = re.compile(r"(?<=[.!?])\s+")
_PAGE_MARKER_RE = re.compile(r"\[Page\s+\d+\]", flags=re.IGNORECASE)
_TOC_LEADER_RE = re.compile(r"[.\u2026·•]{3,}\s*\d*")
_LONG_DECORATION_RE = re.compile(r"[_=\-–—]{3,}")
_MARKDOWN_LINK_RE = re.compile(
    r"\[[^\]]+\]\(((?:https?://|www\.)[^)\s]+)\)",
    flags=re.IGNORECASE,
)
_HTML_LINK_RE = re.compile(
    r"<a\b[^>]*\bhref\s*=\s*['\"]((?:https?://|www\.)[^'\"]+)['\"][^>]*>.*?</a>",
    flags=re.IGNORECASE | re.DOTALL,
)
_AUTOLINK_RE = re.compile(r"<((?:https?://|www\.)[^>\s]+)>", flags=re.IGNORECASE)
_URL_TOKEN_RE = re.compile(
    r"(?<![\w@])(?:(?:https?|ftp)://|www\.)[^\s<>\[\]{}]+",
    flags=re.IGNORECASE,
)
_BARE_DOMAIN_RE = re.compile(
    r"(?<![\w@])(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}(?:/[^\s<>\[\]{}]*)?",
    flags=re.IGNORECASE,
)
_EMAIL_RE = re.compile(
    r"(?<![\w.+-])[\w.+-]+@[a-z0-9-]+(?:\.[a-z0-9-]+)+(?=$|[\s.,;:!?])",
    flags=re.IGNORECASE,
)
_INLINE_FOOTNOTE_RE = re.compile(r"(?<=[.!?;:»”\"])\s*\d{1,2}(?=\s|$)")
_PAUSE_MARKER_RE = re.compile(
    r"\[PAUSE\s*:\s*(?P<seconds>\d+(?:\.\d+)?)\s*\]",
    flags=re.IGNORECASE,
)

_ABBREVIATIONS = {
    "dr.",
    "ifj.",
    "id.",
    "kb.",
    "pl.",
    "stb.",
    "ún.",
    "u.",
    "utca.",
    "mr.",
    "mrs.",
    "ms.",
    "prof.",
    "e.g.",
    "i.e.",
    "ill.",
    "vö.",
    "ld.",
    "l.",
    "sz.",
    "szám.",
    "hrsz.",
    "tel.",
    "fax.",
    "jan.",
    "febr.",
    "márc.",
    "ápr.",
    "máj.",
    "jún.",
    "júl.",
    "aug.",
    "szept.",
    "okt.",
    "nov.",
    "dec.",
}

DEFAULT_PRONUNCIATIONS: dict[str, dict[str, str]] = {
    "hu": {
        "Kft.": "káefté",
        "Zrt.": "zártkörűen működő részvénytársaság",
        "Bt.": "betéti társaság",
        "KSH": "káeshá",
        "MTA": "em té á",
        "AI": "ááj",
    },
    "en": {
        "e.g.": "for example",
        "i.e.": "that is",
        "etc.": "et cetera",
        "AI": "A I",
    },
}


@dataclass(frozen=True)
class SpeechTextOptions:
    """Options for the final, speech-oriented text pass before TTS."""

    link_mode: str = "domain"
    dynamic_pauses: bool = True
    paragraph_pause: float = 0.75
    clause_pause: float = 0.28
    pronunciation_map: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ProsodyProfile:
    paragraph_pause: float
    clause_pause: float


PROSODY_PROFILES: dict[str, ProsodyProfile] = {
    "natural": ProsodyProfile(paragraph_pause=0.75, clause_pause=0.28),
    "calm": ProsodyProfile(paragraph_pause=0.95, clause_pause=0.34),
    "compact": ProsodyProfile(paragraph_pause=0.52, clause_pause=0.20),
}


def get_prosody_profile(name: str) -> ProsodyProfile:
    return PROSODY_PROFILES.get(name, PROSODY_PROFILES["natural"])


def parse_pronunciation_map(raw: str | Mapping[str, str] | None) -> dict[str, str]:
    """Parse ``source = spoken form`` lines from the UI or CLI."""
    if raw is None:
        return {}
    if isinstance(raw, Mapping):
        return {
            str(source).strip(): str(replacement).strip()
            for source, replacement in raw.items()
            if str(source).strip() and str(replacement).strip()
        }

    result: dict[str, str] = {}
    for line in str(raw).splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=>" in line:
            source, replacement = line.split("=>", 1)
        elif "=" in line:
            source, replacement = line.split("=", 1)
        else:
            continue
        source = source.strip()
        replacement = replacement.strip()
        if source and replacement:
            result[source] = replacement
    return result


def clean_text(text: str, *, link_mode: str = "domain") -> str:
    """Clean document extraction artefacts while keeping the text editable."""
    if link_mode not in {"domain", "skip", "full"}:
        raise ValueError(f"Unknown link mode: {link_mode}")

    text = unicodedata.normalize("NFKC", text)
    text = _remove_invisible_controls(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _normalize_hungarian_legacy_accents(text)
    text = _normalize_links(text, link_mode=link_mode)
    text = _mark_heading_breaks(text)
    text = _PAGE_MARKER_RE.sub("", text)
    text = _TOC_LEADER_RE.sub(" ", text)
    text = _LONG_DECORATION_RE.sub(" ", text)
    text = _INLINE_FOOTNOTE_RE.sub("", text)
    text = _HYPHEN_LINEBREAK_RE.sub(r"\1\2", text)
    text = _SOFT_LINEBREAK_RE.sub(" ", text)
    text = _MULTISPACE_RE.sub(" ", text)
    text = _normalize_punctuation_spacing(text)
    text = _BLANK_LINES_RE.sub("\n\n", text)
    return text.strip()


def prepare_speech_text(
    text: str,
    language: str,
    options: SpeechTextOptions | None = None,
) -> str:
    """Create the deterministic text that is actually sent to the normalizer/TTS."""
    if language not in {"hu", "en"}:
        raise ValueError(f"Unsupported speech language: {language}")
    options = options or SpeechTextOptions()
    text = clean_text(text, link_mode=options.link_mode)
    text = _replace_emails_for_speech(text, language)
    text = _replace_web_addresses_for_speech(text, language, options.link_mode)
    text = _replace_speech_symbols(text, language)
    text = _apply_pronunciations(text, language, options.pronunciation_map)
    if options.dynamic_pauses:
        text = add_dynamic_pauses(
            text,
            paragraph_pause=options.paragraph_pause,
            clause_pause=options.clause_pause,
        )
    return text


def add_dynamic_pauses(text: str, paragraph_pause: float = 0.75, clause_pause: float = 0.28) -> str:
    """Add restrained pauses at paragraph and clause boundaries.

    Sentence pauses remain Piper's job. Only the longer structural boundaries are
    marked here, so normal prose does not become choppy.
    """
    if not text.strip():
        return text

    clause_marker = f"[PAUSE:{_format_pause(clause_pause)}]"
    text = re.sub(
        r"([;:])[ \t]+(?=\S)",
        lambda match: f"{match.group(1)} {clause_marker} ",
        text,
    )

    paragraphs = text.split("\n\n")
    for index in range(len(paragraphs) - 1):
        paragraph = paragraphs[index].rstrip()
        if paragraph and not re.search(r"\[PAUSE\s*:\s*\d+(?:\.\d+)?\s*\]\s*$", paragraph, flags=re.IGNORECASE):
            paragraph += f" [PAUSE:{_format_pause(paragraph_pause)}]"
        paragraphs[index] = paragraph
    return "\n\n".join(paragraphs)


def _format_pause(seconds: float) -> str:
    value = max(0.05, min(float(seconds), 30.0))
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _remove_invisible_controls(text: str) -> str:
    return "".join(
        character
        for character in text
        if character in "\n\t" or unicodedata.category(character) not in {"Cc", "Cf"}
    )


def _normalize_punctuation_spacing(text: str) -> str:
    text = re.sub(r"[ \t]+([,.;:!?])", r"\1", text)
    text = re.sub(r"([([{])[ \t]+", r"\1", text)
    return re.sub(r"[ \t]+([)\]}])", r"\1", text)


def _normalize_links(text: str, *, link_mode: str) -> str:
    def replace_url(match: re.Match[str]) -> str:
        return _link_replacement(match.group(1), link_mode)

    text = _HTML_LINK_RE.sub(replace_url, text)
    text = _MARKDOWN_LINK_RE.sub(replace_url, text)
    text = _AUTOLINK_RE.sub(replace_url, text)

    def replace_raw(match: re.Match[str]) -> str:
        return _link_replacement(match.group(0), link_mode)

    text = _URL_TOKEN_RE.sub(replace_raw, text)
    return _BARE_DOMAIN_RE.sub(replace_raw, text)


def _link_replacement(value: str, link_mode: str) -> str:
    value = value.strip()
    if link_mode == "skip":
        return " "
    if link_mode == "full":
        return value

    candidate = _strip_url_tail(value)
    parsed = urlsplit(candidate if "://" in candidate else f"//{candidate}")
    host = parsed.hostname or candidate
    return host.removeprefix("www.")


def _strip_url_tail(value: str) -> str:
    while value and value[-1] in ".,;:!?":
        value = value[:-1]
    if value.endswith(")") and value.count(")") > value.count("("):
        value = value[:-1]
    return value


def _replace_emails_for_speech(text: str, language: str) -> str:
    connector = "kukac" if language == "hu" else "at"
    dot = "pont" if language == "hu" else "dot"
    underscore = "aláhúzásjel" if language == "hu" else "underscore"
    hyphen = "kötőjel" if language == "hu" else "hyphen"

    def replace(match: re.Match[str]) -> str:
        local, domain = match.group(0).split("@", 1)
        local = local.replace("_", f" {underscore} ").replace("-", f" {hyphen} ")
        local = local.replace(".", f" {dot} ")
        domain = domain.replace("-", f" {hyphen} ").replace(".", f" {dot} ")
        return f"{local} {connector} {domain}"

    return _EMAIL_RE.sub(replace, text)


def _replace_web_addresses_for_speech(text: str, language: str, link_mode: str) -> str:
    if link_mode == "skip":
        return text
    dot = "pont" if language == "hu" else "dot"
    slash = "per" if language == "hu" else "slash"
    colon = "kettőspont" if language == "hu" else "colon"
    hyphen = "kötőjel" if language == "hu" else "hyphen"

    def replace(match: re.Match[str]) -> str:
        raw = _strip_url_tail(match.group(0))
        parsed = urlsplit(raw if "://" in raw else f"//{raw}")
        host = parsed.hostname or raw
        host = host.removeprefix("www.")
        spoken = host.replace("-", f" {hyphen} ").replace(".", f" {dot} ")
        if link_mode == "full" and parsed.scheme:
            spoken = f"{parsed.scheme} {colon} {slash} {slash} {spoken}"
        if link_mode == "full" and parsed.path and parsed.path != "/":
            path = parsed.path.strip("/").replace("-", f" {hyphen} ").replace("/", f" {slash} ")
            spoken = f"{spoken} {slash} {path}"
        return spoken

    text = _URL_TOKEN_RE.sub(replace, text)
    return _BARE_DOMAIN_RE.sub(replace, text)


def _replace_speech_symbols(text: str, language: str) -> str:
    conjunction = "és" if language == "hu" else "and"
    return re.sub(r"\s*&\s*", f" {conjunction} ", text)


def _apply_pronunciations(text: str, language: str, custom: Mapping[str, str]) -> str:
    replacements = dict(DEFAULT_PRONUNCIATIONS.get(language, {}))
    replacements.update(parse_pronunciation_map(custom))
    for source, replacement in sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True):
        if not source:
            continue
        pattern = re.compile(rf"(?<!\w){re.escape(source)}(?!\w)", flags=re.IGNORECASE)
        text = pattern.sub(lambda _match, value=replacement: value, text)
    return text


def _normalize_hungarian_legacy_accents(text: str) -> str:
    return text.translate(
        str.maketrans(
            {
                "ô": "ő",
                "Ô": "Ő",
                "û": "ű",
                "Û": "Ű",
            }
        )
    )


def _mark_heading_breaks(text: str) -> str:
    marked: list[str] = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped and _looks_like_heading(stripped) and stripped[-1] not in ".!?;:":
            marked.append(f"{line}.")
        else:
            marked.append(line)
    return "\n".join(marked)


def _looks_like_heading(line: str) -> bool:
    letters = [char for char in line if char.isalpha()]
    if not letters:
        return False
    upper_ratio = sum(1 for char in letters if char.isupper()) / len(letters)
    if upper_ratio > 0.72 and len(letters) >= 6:
        return True
    if re.match(r"^\d+(?:\.\d+)*\.?\s+\S+", line) and len(line) < 90:
        return True
    return False


def chunk_text(text: str, max_chars: int = 1_200) -> list[str]:
    paragraphs = [p.strip() for p in clean_text(text).split("\n\n") if p.strip()]
    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        sentences = _split_sentences(paragraph)
        for sentence in sentences:
            if not sentence:
                continue
            candidate = f"{current.rstrip()} {sentence}".strip() if current else sentence
            if len(candidate) <= max_chars:
                current = candidate
                continue
            if current:
                chunks.append(current)
            if len(sentence) <= max_chars:
                current = sentence
            else:
                pieces = _split_long_sentence(sentence, max_chars)
                chunks.extend(pieces[:-1])
                current = pieces[-1] if pieces else ""

        if current and len(current) + 2 <= max_chars:
            current = f"{current}\n\n"

    if current.strip():
        chunks.append(current.strip())
    return chunks


def _split_sentences(paragraph: str) -> list[str]:
    protected = paragraph
    replacements: dict[str, str] = {}
    protected = _protect_matches(protected, _NUMERIC_INTERNAL_DOT_RE, "NUMDOT", replacements)
    for index, abbreviation in enumerate(_ABBREVIATIONS):
        token = f"__ABBR_{index}__"
        pattern = re.compile(re.escape(abbreviation), flags=re.IGNORECASE)
        protected = pattern.sub(lambda m, t=token: _store_replacement(m.group(0), t, replacements), protected)

    parts = _SENTENCE_END_RE.split(protected)
    sentences = []
    for part in parts:
        for token, original in replacements.items():
            part = part.replace(token, original)
        sentences.append(part.strip())
    return sentences


def _protect_matches(
    text: str,
    pattern: re.Pattern[str],
    prefix: str,
    replacements: dict[str, str],
) -> str:
    def replace(match: re.Match[str]) -> str:
        token = f"__{prefix}_{len(replacements)}__"
        return _store_replacement(match.group(0), token, replacements)

    return pattern.sub(replace, text)


def _store_replacement(original: str, token: str, replacements: dict[str, str]) -> str:
    replacements[token] = original
    return token


def _split_long_sentence(sentence: str, max_chars: int) -> list[str]:
    words = sentence.split()
    pieces: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip() if current else word
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                pieces.append(current)
            current = word
    if current:
        pieces.append(current)
    return pieces

