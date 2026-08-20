#!/usr/bin/env python3
"""Read-only audit for invisible Unicode characters in UTF-8 text."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import unicodedata


CHARACTERS = {
    0x200B: "zero_width",
    0x200C: "zero_width_non_joiner",
    0x200D: "zero_width_joiner",
    0x2060: "word_joiner",
    0xFEFF: "zero_width_no_break_space",
}
BIDI_CONTROLS = frozenset(range(0x202A, 0x202F)) | frozenset(range(0x2066, 0x206A))


def _in_ranges(codepoint: int, ranges: tuple[tuple[int, int], ...]) -> bool:
    return any(start <= codepoint <= end for start, end in ranges)


def _is_joining_script(character: str) -> bool:
    if not character:
        return False
    return _in_ranges(
        ord(character),
        (
            (0x0600, 0x06FF),  # Arabic
            (0x0700, 0x074F),  # Syriac
            (0x0750, 0x077F),  # Arabic Supplement
            (0x08A0, 0x08FF),  # Arabic Extended-A
            (0x1800, 0x18AF),  # Mongolian
        ),
    )


def _is_emoji_like(character: str) -> bool:
    if not character:
        return False
    codepoint = ord(character)
    return (
        _in_ranges(codepoint, ((0x1F000, 0x1FAFF), (0x2600, 0x27BF)))
        or unicodedata.category(character) == "So"
    )


def _is_semantic_joiner(text: str, index: int, codepoint: int) -> bool:
    previous = text[index - 1] if index else ""
    following = text[index + 1] if index + 1 < len(text) else ""
    if codepoint == 0x200C:
        return _is_joining_script(previous) and _is_joining_script(following)
    if codepoint == 0x200D:
        return (
            _is_emoji_like(previous) and _is_emoji_like(following)
            or _is_joining_script(previous) and _is_joining_script(following)
        )
    return False


def _location(text: str, index: int) -> tuple[int, int]:
    line = text.count("\n", 0, index) + 1
    last_newline = text.rfind("\n", 0, index)
    column = index - last_newline
    return line, column


def _context(text: str, index: int, radius: int = 12) -> str:
    start = max(0, index - radius)
    end = min(len(text), index + radius + 1)
    pieces = []
    for character in text[start:end]:
        codepoint = ord(character)
        if codepoint in CHARACTERS or codepoint in BIDI_CONTROLS:
            pieces.append(f"<U+{codepoint:04X}>")
        elif character == "\n":
            pieces.append("\\n")
        elif character == "\r":
            pieces.append("\\r")
        elif character == "\t":
            pieces.append("\\t")
        else:
            pieces.append(character)
    return "".join(pieces)


def audit_text(text: str) -> dict[str, object]:
    findings = []
    for index, character in enumerate(text):
        codepoint = ord(character)
        if codepoint not in CHARACTERS and codepoint not in BIDI_CONTROLS:
            continue

        if codepoint in BIDI_CONTROLS:
            kind = "bidi_control"
            classification = "suspicious"
        elif codepoint == 0xFEFF and index == 0:
            kind = "byte_order_mark"
            classification = "informational"
        else:
            kind = CHARACTERS[codepoint]
            classification = (
                "likely_semantic"
                if _is_semantic_joiner(text, index, codepoint)
                else "suspicious"
            )

        line, column = _location(text, index)
        findings.append(
            {
                "index": index,
                "line": line,
                "column": column,
                "codepoint": f"U+{codepoint:04X}",
                "name": unicodedata.name(character, "UNKNOWN"),
                "kind": kind,
                "classification": classification,
                "context": _context(text, index),
            }
        )

    actionable_count = sum(
        finding["classification"] == "suspicious" for finding in findings
    )
    counts = dict(Counter(finding["codepoint"] for finding in findings))
    return {
        "hidden_artifacts": "found" if actionable_count else "none",
        "statistical_watermark": "unknown",
        "actionable_count": actionable_count,
        "finding_count": len(findings),
        "counts": counts,
        "findings": findings,
    }


def audit_file(path: str | Path) -> dict[str, object]:
    source = Path(path)
    text = source.read_text(encoding="utf-8", errors="strict")
    result = audit_text(text)
    result["path"] = str(source)
    return result


def _print_human(result: dict[str, object]) -> None:
    print(f"hidden artifacts: {result['hidden_artifacts']}")
    print(f"statistical watermark: {result['statistical_watermark']}")
    print(f"actionable findings: {result['actionable_count']}")
    for finding in result["findings"]:
        print(
            f"{finding['line']}:{finding['column']} {finding['codepoint']} "
            f"{finding['name']} [{finding['classification']}] "
            f"context={finding['context']!r}"
        )


def _configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    _configure_stdio()
    parser = argparse.ArgumentParser(
        description="Audit a UTF-8 text file for invisible Unicode characters."
    )
    parser.add_argument("path", type=Path)
    parser.add_argument("--json", action="store_true", help="emit JSON")
    args = parser.parse_args(argv)

    try:
        result = audit_file(args.path)
    except UnicodeDecodeError:
        print(f"error: {args.path} is not valid UTF-8", file=sys.stderr)
        return 2
    except OSError as error:
        print(f"error: cannot read {args.path}: {error}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        _print_human(result)
    return 1 if result["actionable_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
