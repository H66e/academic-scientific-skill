#!/usr/bin/env python3
"""De-format effect-pilot artifacts before blind review.

This is a deliberately small, deterministic text transform. It never touches the
network, never writes bytecode, and never modifies its input in place unless an
explicit ``--out`` file is supplied.

Removed content:

* fenced code blocks whose info string is exactly ``nearest-set-json`` or
  ``provisional-json`` (fences included);
* HTML comments, including ``<!-- report-tier: ... -->`` markers;
* standalone ``report-tier: ...`` marker lines;
* bracketed claim IDs such as ``[C1]`` or ``[C12]`` (and comma-separated lists).

Everything else, including prose, headings, ordinary code fences, citation
markers such as ``[1]``, case, and language, is preserved.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True

MACHINE_INFOS = frozenset({"nearest-set-json", "provisional-json"})

_OPENING_FENCE = re.compile(
    r"^(?P<indent>[ \t]*)(?P<fence>`{3,}|~{3,})(?P<info>[^\r\n]*)$"
)
_CLOSING_FENCE = re.compile(r"^[ \t]*(?P<fence>`{3,}|~{3,})[ \t]*$")
_REPORT_TIER_LINE = re.compile(
    r"^[ \t]*report-tier\s*:\s*[^\r\n]*(?:\r?\n|$)", re.MULTILINE
)
_CLAIM_ID = re.compile(
    r"(?P<pre>[ \t]*)\[C\d+(?:\s*[,，;；]\s*C\d+)*\](?P<post>[ \t]*)"
)

# Characters that usually want a separator on their right when a claim ID is
# removed (structural markers, an opening bracket, or a colon/comma).
_LEFT_SEPARATORS = frozenset(",;:.|>#-*+•，；：、")
_OPENERS = frozenset("([{（【《「『\"'")
# Closing punctuation and sentence punctuation: no space should be inserted.
_RIGHT_PUNCT = frozenset(".,;:!?)]}>，。；：！？）】》」』、")


def _line_body(line: str) -> str:
    """Return a line without its trailing newline characters."""
    return line.rstrip("\r\n")


def _is_cjk(character: str) -> bool:
    """True for common CJK Unified Ideographs (used only to avoid adding spaces)."""
    if not character:
        return False
    code = ord(character)
    return (
        0x3400 <= code <= 0x4DBF
        or 0x4E00 <= code <= 0x9FFF
        or 0xF900 <= code <= 0xFAFF
    )


def _strip_machine_blocks(text: str) -> str:
    """Remove target fenced blocks, respecting ordinary fences and their content."""
    lines = text.splitlines(keepends=True)
    output: list[str] = []
    index = 0

    while index < len(lines):
        body = _line_body(lines[index])
        opening = _OPENING_FENCE.match(body)
        if opening is None:
            output.append(lines[index])
            index += 1
            continue

        fence = opening.group("fence")
        fence_char = fence[0]
        fence_length = len(fence)
        info = opening.group("info").strip()

        if info in MACHINE_INFOS:
            # Drop the opening fence and everything through the matching close.
            # An unclosed target block is dropped to end-of-file so machine
            # content cannot leak into the blind artifact.
            index += 1
            while index < len(lines):
                closing = _CLOSING_FENCE.match(_line_body(lines[index]))
                if (
                    closing is not None
                    and closing.group("fence")[0] == fence_char
                    and len(closing.group("fence")) >= fence_length
                ):
                    index += 1
                    break
                index += 1
            continue

        # An ordinary fenced block is copied verbatim. Its content is not
        # reinterpreted, so a code sample containing a target fence stays intact.
        output.append(lines[index])
        index += 1
        while index < len(lines):
            output.append(lines[index])
            closing = _CLOSING_FENCE.match(_line_body(lines[index]))
            if (
                closing is not None
                and closing.group("fence")[0] == fence_char
                and len(closing.group("fence")) >= fence_length
            ):
                index += 1
                break
            index += 1

    return "".join(output)


def _strip_html_comments(text: str) -> str:
    """Remove complete HTML comments; an unclosed comment is dropped to EOF."""
    pieces: list[str] = []
    position = 0
    while True:
        start = text.find("<!--", position)
        if start < 0:
            pieces.append(text[position:])
            return "".join(pieces)
        pieces.append(text[position:start])
        end = text.find("-->", start + 4)
        if end < 0:
            return "".join(pieces)
        position = end + 3


def _strip_report_tier_lines(text: str) -> str:
    """Remove standalone ``report-tier: ...`` marker lines."""
    return _REPORT_TIER_LINE.sub("", text)


def _needs_separator(before: str, after: str) -> bool:
    """Decide whether removing a claim ID should leave one space.

    The goal is to keep words separate without inserting spaces around
    punctuation or between CJK characters.
    """
    if not before or not after:
        return False
    if _is_cjk(before) and _is_cjk(after):
        return False
    if before in "，；：、。！？" and _is_cjk(after):
        return False
    if after in _RIGHT_PUNCT:
        return False

    left = (
        before.isalnum()
        or before == "_"
        or before in _LEFT_SEPARATORS
        or before in _OPENERS
    )
    right = (
        after.isalnum()
        or after == "_"
        or after in _OPENERS
        or after == "|"
    )
    return left and right


def _strip_claim_ids(text: str) -> str:
    """Remove bracketed claim IDs and clean up only the adjacent spacing."""

    def replace(match: re.Match[str]) -> str:
        start, end = match.span()
        pre = match.group("pre")

        # If the token is the first non-indent content on its line, keep the
        # indentation and remove the token plus the following horizontal space.
        line_start = text.rfind("\n", 0, start) + 1
        if text[line_start:start].strip(" \t") == "":
            return pre

        before = text[start - 1] if start > 0 else ""
        after = text[end] if end < len(text) else ""
        return " " if _needs_separator(before, after) else ""

    return _CLAIM_ID.sub(replace, text)


def strip_artifact(text: str) -> str:
    """Return ``text`` with machine formatting removed.

    This function has no side effects and prints nothing. It is deterministic:
    the same input always returns the same output, and the transform is
    idempotent for already-stripped text.
    """
    if not isinstance(text, str):
        raise TypeError("strip_artifact() requires a str")
    text = _strip_machine_blocks(text)
    text = _strip_html_comments(text)
    text = _strip_report_tier_lines(text)
    text = _strip_claim_ids(text)
    return text


def _write_stdout(text: str) -> None:
    """Write UTF-8 bytes to stdout when possible, independent of console locale."""
    data = text.encode("utf-8")
    buffer = getattr(sys.stdout, "buffer", None)
    if buffer is not None:
        buffer.write(data)
    else:
        sys.stdout.write(text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="strip_artifact.py",
        description="Remove machine formatting from an effect-pilot artifact.",
    )
    parser.add_argument("input", type=Path, help="UTF-8 input artifact")
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="write the transformed text here instead of stdout",
    )
    args = parser.parse_args(argv)

    try:
        with open(args.input, "r", encoding="utf-8", newline="") as handle:
            text = handle.read()
    except OSError as exc:
        print(f"error: cannot read {args.input}: {exc}", file=sys.stderr)
        return 2

    result = strip_artifact(text)

    if args.out is None:
        _write_stdout(result)
        return 0

    try:
        with open(args.out, "w", encoding="utf-8", newline="") as handle:
            handle.write(result)
    except OSError as exc:
        print(f"error: cannot write {args.out}: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
