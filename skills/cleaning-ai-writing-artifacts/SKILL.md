---
name: cleaning-ai-writing-artifacts
description: Use when finalizing user-facing prose documents such as cover letters, application essays, reports, proposals, formal summaries, or similar long-form writing where AI-origin artifacts should be audited before delivery.
---

# Cleaning AI Writing Artifacts

## Overview

Audit document prose for hidden Unicode artifacts and conspicuously synthetic writing patterns, then clean them without changing facts, claims, citations, numbers, or the author's intended meaning.

Treat "AI watermark" as three different things:
1. hidden/formatting characters,
2. stylistic patterns that may look machine-written,
3. provider-specific statistical watermarks.

Only the first category can be determined from plain text with confidence. Style is not proof of AI authorship. Statistical watermarks require a compatible detector or watermark key.

## When to Use

Use this skill only for document-oriented prose work, especially:
- cover letters and application essays
- reports and formal summaries
- proposals, memos, and long-form documentation
- final polishing of prose intended to be submitted or published

Do not invoke it for ordinary chat, coding, debugging, algorithm explanations, short Q&A, or raw note-taking unless the user explicitly requests an audit.

## Procedure

### 1. Preserve the source
Before editing, preserve:
- factual meaning
- concrete experiences and examples
- numbers, dates, names, citations, URLs
- requested tone, length, and document structure

Do not invent personal experience to make prose sound more human.

### 2. Inspect hidden Unicode
Check for suspicious invisible or control characters, especially:
- U+200B ZERO WIDTH SPACE
- U+200C ZERO WIDTH NON-JOINER
- U+200D ZERO WIDTH JOINER
- U+2060 WORD JOINER
- U+FEFF ZERO WIDTH NO-BREAK SPACE/BOM
- unexpected bidi controls in U+202A–U+202E and U+2066–U+2069

For a file audit, use `scripts/audit_unicode.py` when Python is already available:

```bash
python scripts/audit_unicode.py INPUT
python scripts/audit_unicode.py INPUT --json
```

The helper is optional and read-only. Do not install Python solely to run it without user approval. If Python is unavailable, use the environment's existing text or code tools to enumerate the same code points and report their positions. If no code-point-aware inspection is possible, report the audit as inconclusive instead of claiming the text is clean.

Treat a leading U+FEFF byte-order mark as informational. Treat U+200C and U+200D as context-sensitive because they may be required by joining scripts or emoji sequences. Do not infer AI authorship from any hidden character.

An audit does not authorize editing. Remove characters only when the user requests cleanup and they are unintended. Preserve characters required for legitimate scripts, emoji sequences, or document semantics. Normalize ordinary prose to Unicode NFC only during an authorized cleanup.

### 3. Audit synthetic writing patterns
Treat these as editing signals, never as proof of AI generation:
- repeated "not only X but also Y" / "단순히 X를 넘어" constructions
- mechanical transitions such as repeated "또한", "이를 통해", "더 나아가", "궁극적으로"
- excessive three-part parallel lists
- vague claims without concrete evidence
- inflated abstractions, generic enthusiasm, or unnecessary conclusions
- uniform sentence length and repeated paragraph structure
- excessive headings, colons, em dashes, or summary restatements

Rewrite only where it improves naturalness, specificity, rhythm, or author voice.

### 4. Handle statistical watermarks correctly
Do not claim that a provider-specific statistical watermark exists or has been removed unless a compatible detector actually verifies it.

If no detector is available, classify statistical watermark status as `unknown`. A rewrite may alter statistical patterns, but never guarantee detector evasion or watermark removal.

### 5. Final verification
Re-read the cleaned text and confirm:
- no accidental meaning change
- no lost evidence, metrics, citations, or constraints
- no suspicious invisible characters remain in normal Korean/English prose
- the prose sounds specific to the author's content rather than generically "humanized"

## Output Contract

For normal document drafting/editing:
- silently apply cleanup before returning the final document
- do not append an "AI detector score"
- do not claim the document is "undetectable"

For an explicit watermark audit:
- report `hidden artifacts: found/none`
- report `statistical watermark: detected/not detected/unknown`
- list code points, locations, and context-sensitive findings
- do not modify the source or provide a rewritten version unless cleanup was also requested
