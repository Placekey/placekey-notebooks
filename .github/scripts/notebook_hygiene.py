#!/usr/bin/env python3
"""Block PRs that commit personal paths, hardcoded keys, or stale placeholders.

Scans .ipynb cell sources only — outputs are ignored here (the secret scanner
covers those). Exits non-zero on any violation.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
NOTEBOOKS = sorted(ROOT.glob("notebooks/*.ipynb"))

# Patterns we refuse to merge into source cells.
PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("personal macOS path", re.compile(r"/Users/[A-Za-z0-9_.-]+/")),
    ("personal linux path", re.compile(r"/home/[A-Za-z0-9_.-]+/")),
    ("hardcoded api_key literal",
     re.compile(r"""api_key\s*=\s*["'](?!your|<|ENTER|\{)[A-Za-z0-9_\-]{12,}["']""", re.IGNORECASE)),
    ("placeholder api key string",
     re.compile(r"""(ENTER YOUR API KEY HERE|your_placekey_api_key|<your placekey api key>)""")),
    # Match `!pip install ... placekey ...` where `placekey` has no version
    # specifier immediately after. Tolerates intervening flags (-q, --upgrade,
    # --user, etc.). Allows `placekey-py` (a different package) and any token
    # that starts with `placekey[<>=~!]` or `placekey==`.
    ("unpinned pip install placekey",
     re.compile(r"!pip install(?:\s+-{1,2}[\w-]+)*\s+placekey(?![\-a-zA-Z0-9_])(?!\s*[<>=~!])")),
    ("AWS access key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("generic bearer token", re.compile(r"Bearer\s+[A-Za-z0-9_\-\.=]{24,}")),
]

# Allow-list substrings that mark a cell as intentionally-demonstrative
# (e.g. markdown explaining what a placeholder looks like).
ALLOWED_CONTEXTS: list[str] = []


def violations_in_cell(cell: dict) -> list[str]:
    source = cell.get("source", "")
    if isinstance(source, list):
        source = "".join(source)
    if not source:
        return []
    if any(marker in source for marker in ALLOWED_CONTEXTS):
        return []
    hits = []
    for label, pat in PATTERNS:
        if pat.search(source):
            hits.append(label)
    return hits


def main() -> int:
    failures: list[str] = []
    for nb_path in NOTEBOOKS:
        try:
            nb = json.loads(nb_path.read_text())
        except Exception as e:
            failures.append(f"{nb_path}: cannot parse JSON ({e})")
            continue
        for idx, cell in enumerate(nb.get("cells", [])):
            hits = violations_in_cell(cell)
            for h in hits:
                failures.append(f"{nb_path.relative_to(ROOT)}: cell {idx}: {h}")
    if failures:
        print("Notebook hygiene failures:\n  - " + "\n  - ".join(failures))
        return 1
    print(f"OK — {len(NOTEBOOKS)} notebook(s) passed hygiene checks.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
