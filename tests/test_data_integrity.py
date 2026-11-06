"""Pin the committed sample data against a SHA256 manifest.

Covers the census block group shapefile read by advanced_functionality and the
two POI fixtures read by Adding_Placekey_to_your_POI_dataset_... and
Placekey_py_Simple_Getting_Started_Bulk — all three are notebook INPUTS, so a
silent edit to any of them changes what CI proves without changing any code. If
one is edited or corrupted, CI fails and the offending checksum is reported. To
accept a legitimate change, regenerate data/checksums.sha256 via:

    (cd data && shasum -a 256 CA_2019_census_block_groups_sample/* \\
        my_places_data_missing.csv bulk_sample_places.csv) > data/checksums.sha256

tests/test_notebook_data.py is the other half of this: it pins what the current
geopandas/pandas stack PARSES out of these bytes, which a checksum cannot.
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
