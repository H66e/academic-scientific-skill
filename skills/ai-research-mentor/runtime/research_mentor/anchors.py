"""Exact, normalized quote anchoring with reproducible hashes."""
from __future__ import annotations
import hashlib
import re
import unicodedata

class AnchorError(ValueError):
    pass

def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFC", value).replace("\u00a0", " ")
    return re.sub(r"\s+", " ", value).strip()

def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

def quote_text(source_id: str, text: str, excerpt: str, *, locator: str = "") -> dict:
    if not isinstance(text, str) or not text:
        raise AnchorError("source text is empty")
    if not isinstance(excerpt, str) or not excerpt.strip():
        raise AnchorError("quote is empty")
    normalized_source = normalize_text(text)
    normalized_quote = normalize_text(excerpt)
    if len(normalized_quote) < 8:
        raise AnchorError("quote must contain at least 8 normalized characters")
    position = normalized_source.find(normalized_quote)
    if position < 0:
        raise AnchorError("quote was not found in acquired source after normalization")
    if normalized_source.find(normalized_quote, position + 1) >= 0:
        raise AnchorError("quote is ambiguous; provide a longer excerpt or select a source block")
    # The normalized offsets are deterministic across platforms.  Original byte
    # offsets are intentionally omitted when whitespace normalization changes them.
    return {
        "source": source_id,
        "locator": locator or "text",
        "start": position,
        "end": position + len(normalized_quote),
        "quote": excerpt,
        "quote_normalized": normalized_quote,
        "quote_sha256": sha256_text(normalized_quote),
        "source_sha256": sha256_text(normalized_source),
        "match": "exact",
        "anchor_version": "text-normalized-v1",
    }
