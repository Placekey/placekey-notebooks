"""Pin the committed sample shapefile against a SHA256 manifest.

If one of the shapefile's sibling files is edited or corrupted, CI fails and
the offending checksum is reported. To accept a legitimate change, regenerate
data/checksums.sha256 via:

    (cd data && shasum -a 256 CA_2019_census_block_groups_sample/*) \\
        > data/checksums.sha256
"""
from __future__ import annotations

import hashlib
import pathlib

DATA_DIR = pathlib.Path(__file__).resolve().parents[1] / "data"
MANIFEST = DATA_DIR / "checksums.sha256"


def _sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def test_manifest_exists():
    assert MANIFEST.is_file(), f"missing manifest: {MANIFEST}"


def test_committed_data_matches_manifest():
    expected: dict[str, str] = {}
    for line in MANIFEST.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        digest, rel = line.split(None, 1)
        expected[rel.strip()] = digest

    mismatches: list[str] = []
    for rel, want in expected.items():
        path = DATA_DIR / rel
        assert path.is_file(), f"referenced data file missing: {rel}"
        got = _sha256(path)
        if got != want:
            mismatches.append(f"{rel}: expected {want}, got {got}")

    assert not mismatches, "data file checksum mismatch:\n  " + "\n  ".join(mismatches)
