from __future__ import annotations

import re
import unicodedata


_MULTISPACE_RE = re.compile(r"[ \t]+")
_BLANK_LINES_RE = re.compile(r"\n{3,}")
_NUMERIC_INTERNAL_DOT_RE = re.compile(r"(?<=\d)\.(?=\d|\s+[a-záéíóöőúüű])")
_HYPHEN_LINEBREAK_RE = re.compile(r"(\w)-\n(\w)")
_SOFT_LINEBREAK_RE = re.compile(r"(?<![.!?;:])\n(?!\n)")
_SENTENCE_END_RE = re.compile(r"(?<=[.!?])\s+")
_PAGE_MARKER_RE = re.compile(r"\[Page\s+\d+\]", flags=re.IGNORECASE)
_TOC_LEADER_RE = re.compile(r"[.\u2026·•]{3,}\s*\d*")
_LONG_DECORATION_RE = re.compile(r"[_=\-–—]{3,}")
_MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\((https?://[^)\s]+)\)", flags=re.IGNORECASE)
_HTML_LINK_RE = re.compile(
    r"<a\b[^>]*\bhref\s*=\s*['\"](https?://[^'\"]+)['\"][^>]*>.*?</a>",
    flags=re.IGNORECASE | re.DOTALL,
)
_AUTOLINK_RE = re.compile(r"<((?:https?://|www\.)[^>\s]+)>", flags=re.IGNORECASE)
_INLINE_FOOTNOTE_RE = re.compile(r"(?<=[.!?;:»”\"])\s*\d{1,2}(?=\s|$)")

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


def clean_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = _remove_invisible_controls(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _normalize_hungarian_legacy_accents(text)
    text = _normalize_links(text)
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


def _normalize_links(text: str) -> str:
    text = _HTML_LINK_RE.sub(r"\1", text)
    text = _MARKDOWN_LINK_RE.sub(r"\1", text)
    return _AUTOLINK_RE.sub(r"\1", text)


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
            candidate = f"{current} {sentence}".strip() if current else sentence
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

