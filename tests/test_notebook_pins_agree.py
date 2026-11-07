"""Assert every notebook's own `!pip install` can be satisfied by the pins.

WHY THIS IS THE ONLY COVER. Each API-key notebook opens with a hardcoded
range, e.g. `!pip install 'placekey>=0.0.9,<1.0'`, so a reader on a fresh
Colab runtime gets the library. Those lines are guarded by `if IN_COLAB:`, so
**CI never executes them** — which is what stops them re-resolving over the
versions CI installed, and is why no constraint machinery is needed.

The cost of that guard is that nothing in CI runs those lines any more, so
nothing would notice a pin drifting outside a notebook's range. The reader
would: pip raises ResolutionImpossible, and because IPython's `!` escape does
not raise on a non-zero exit, their cell would pass having installed nothing,
leaving the next cell to fail on an import. This file is what prevents that
reaching a reader, and it is the only thing that does.

A failure here must be fixed on one side or the other: widen the notebook's
range in the same pull request as the bump, or hold the pin back. Do not
silence it.

`.github/scripts/notebook_hygiene.py` already refuses an `!pip install
placekey` with NO specifier. This is the other half: a specifier that is
present and no longer agrees with the pin.

`packaging` is not declared anywhere: it is a hard dependency of `pytest`,
which is the only way these tests run, so it is always present when they are.
"""
from __future__ import annotations

import json
import pathlib
import re
import shlex
import tomllib

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
NOTEBOOKS = sorted((REPO_ROOT / "notebooks").glob("*.ipynb"))
PYPROJECT = REPO_ROOT / "pyproject.toml"

PIP_INSTALL = re.compile(r"^\s*[!%]\s*pip\s+install\s+(?P<args>.+?)\s*$", re.MULTILINE)


def pinned_versions() -> dict[str, str]:
    """{canonical distribution name: version} from [project] dependencies."""
    deps = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]["dependencies"]
    pins: dict[str, str] = {}
    for dep in deps:
        req = Requirement(dep)
        exact = [s.version for s in req.specifier if s.operator == "=="]
        assert exact, f"pyproject dependency is not an exact pin: {dep}"
        pins[canonicalize_name(req.name)] = exact[0]
    return pins


def notebook_requirements() -> list[tuple[str, Requirement]]:
    """Every requirement named by a `!pip install` line, with its notebook."""
    found: list[tuple[str, Requirement]] = []
    for path in NOTEBOOKS:
        nb = json.loads(path.read_text(encoding="utf-8"))
        for cell in nb["cells"]:
            if cell["cell_type"] != "code":
                continue
            for match in PIP_INSTALL.finditer("".join(cell["source"])):
                for token in shlex.split(match["args"]):
                    # Flags (-q, --upgrade, ...) and anything that is not a
                    # plain requirement are not version claims.
                    if token.startswith("-") or token.startswith("."):
                        continue
                    found.append((path.name, Requirement(token)))
    return found


def test_parser_finds_a_requirement_in_every_notebook_that_installs():
    """A guard on the parser, checked PER NOTEBOOK.

    If the regex stops matching, every assertion below passes vacuously. A
    single repo-wide "found something" check would not catch that: four
    notebooks install `placekey`, so one of them falling out of the regex
    would be masked by the other three. Calibrate against the raw text
    instead — any notebook whose source mentions `pip install` must yield at
    least one parsed requirement.
    """
    parsed: dict[str, int] = {}
    for notebook, _ in notebook_requirements():
        parsed[notebook] = parsed.get(notebook, 0) + 1

    unparsed: list[str] = []
    for path in NOTEBOOKS:
        nb = json.loads(path.read_text(encoding="utf-8"))
        mentions = any(
            "pip install" in "".join(cell["source"])
            for cell in nb["cells"]
            if cell["cell_type"] == "code"
        )
        if mentions and not parsed.get(path.name):
            unparsed.append(path.name)

    assert not unparsed, (
        "a notebook has a `pip install` the parser did not extract — check PIP_INSTALL:\n  "
        + "\n  ".join(unparsed)
    )
    assert parsed, "parsed no !pip install requirements at all"


def test_every_notebook_requirement_is_a_pinned_distribution():
    # A notebook installing something pyproject does not declare is outside
    # everything that governs versions here: not pinned, not proposed by
    # Dependabot, and not covered by the drift check.
    pins = pinned_versions()
    undeclared = sorted(
        {
            f"{notebook}: {req.name}"
            for notebook, req in notebook_requirements()
            if canonicalize_name(req.name) not in pins
        }
    )
    assert not undeclared, (
        "notebook installs a distribution that pyproject.toml does not pin:\n  "
        + "\n  ".join(undeclared)
        + "\nAdd it to [project] dependencies with an == pin."
    )


def test_pins_satisfy_every_notebook_specifier():
    """The assertion this file exists for. Exact versions against exact ranges.

    A failure means the pin and the notebook have diverged, and must be fixed
    on one side or the other: widen the notebook's range in the same pull
    request as the bump, or hold the pin back. Do not silence it — pip will
    refuse the install in the notebook and the cell will pass anyway.
    """
    pins = pinned_versions()
    conflicts: list[str] = []
    for notebook, req in notebook_requirements():
        name = canonicalize_name(req.name)
        pin = pins.get(name)
        if pin is None:
            continue  # reported by the test above
        if not req.specifier.contains(pin, prereleases=True):
            conflicts.append(
                f"{notebook}: cell asks for `{req}` but pyproject pins {req.name}=={pin}"
            )

    assert not conflicts, (
        "a notebook's !pip install cannot be satisfied by the pinned version.\n"
        "pip would raise ResolutionImpossible, IPython's `!` would NOT raise, and\n"
        "the cell would pass green while installing nothing:\n  "
        + "\n  ".join(sorted(set(conflicts)))
    )
