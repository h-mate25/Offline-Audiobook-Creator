from audiobook_maker.text import (
    SpeechTextOptions,
    add_dynamic_pauses,
    chunk_text,
    clean_text,
    prepare_speech_text,
)


def test_clean_text_reduces_links_to_domain() -> None:
    text = "[Dokumentáció](https://www.example.com/guide?q=1) és <https://docs.example.org/a>."

    cleaned = clean_text(text)

    assert "example.com" in cleaned
    assert "docs.example.org" in cleaned
    assert "https://" not in cleaned
    assert "guide?q" not in cleaned


def test_speech_text_makes_addresses_safe_for_normalizers() -> None:
    text = "Írj a anna.kiss@example.com címre, vagy nézd meg: https://example.com/könyv."

    prepared = prepare_speech_text(text, "hu")

    assert "kukac" in prepared
    assert "pont" in prepared
    assert "@" not in prepared
    assert "https://" not in prepared


def test_custom_pronunciation_and_structural_pauses() -> None:
    text = "A Kft. rövid bemutatása; ez a folytatás.\n\nÚj bekezdés."

    prepared = prepare_speech_text(
        text,
        "hu",
        SpeechTextOptions(
            pronunciation_map={"Kft.": "ká efté"},
            paragraph_pause=0.8,
            clause_pause=0.3,
        ),
    )

    assert "ká efté" in prepared
    assert "[PAUSE:0.3]" in prepared
    assert "[PAUSE:0.8]" in prepared


def test_dynamic_pauses_do_not_create_pause_only_chunks() -> None:
    prepared = add_dynamic_pauses("Első bekezdés.\n\nMásodik bekezdés.")

    chunks = chunk_text(prepared, max_chars=1200)

    assert chunks
    assert all(any(character.isalnum() for character in chunk) for chunk in chunks)
    assert "[PAUSE:0.75]" in chunks[0]


def test_link_can_be_skipped() -> None:
    prepared = prepare_speech_text(
        "A részletek a https://example.com oldalon vannak.",
        "en",
        SpeechTextOptions(link_mode="skip", dynamic_pauses=False),
    )

    assert "example" not in prepared
    assert "https" not in prepared

