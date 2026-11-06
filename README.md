# placekey-notebooks
This repository includes tutorials, such as Jupyter notebooks, Google Sheets guides and more, showcasing the features of the [Placekey](https://placekey.io), the [Placekey API](https://docs.placekey.io/), [Placekey Python library](https://github.com/Placekey/placekey-py) and an expanse of no-code tools.

For more details about Placekey, visit the [Placekey website](https://placekey.io/).

## Setup

1. Clone this repo and install dependencies. `pyproject.toml` declares everything, pinned to exact versions:

   ```bash
   pip install .
   ```

   That is the whole install, on every platform and in CI. There is no lockfile — a lockfile pins one resolve for one interpreter on one operating system, and these are tutorial notebooks meant to keep working against current releases rather than a deployed artifact that needs a reproducible build. Python 3.11 or newer is required; CI runs 3.11 and 3.12.

   To change a version, edit `[project] dependencies` in `pyproject.toml`. Every **runtime** dependency is pinned with `==`, so Dependabot proposes each bump as its own pull request (see `.github/dependabot.yml`) and CI decides whether it lands — there are no version caps and no `ignore:` block to keep in step. The tools that run CI (`nbmake`, `pytest`, `ruff`, `codespell`, `nbformat`, `pip-audit`) are bounded ranges in the workflows' own `run:` blocks and are not Dependabot-managed.

   Four notebooks carry their own `!pip install 'placekey>=0.0.9,<1.0'`, because a reader on a fresh Colab runtime needs it. CI constrains those lines to the installed versions so they cannot resolve past the pins, and checks afterwards that nothing moved; `tests/test_notebook_pins_agree.py` checks the other direction, that each pin still satisfies the range a notebook asks for. Widening a pin past one of those ranges means widening the notebook in the same pull request.

2. Get a Placekey API key — sign up at [placekey.io](https://placekey.io/).

3. Provide the key to the notebooks **without pasting it into a cell**. Pick one:

   - **Environment variable** (recommended):
     ```bash
     export PLACEKEY_API_KEY="your-key-here"
     jupyter lab
     ```
   - **`.env` file** (auto-loaded by `python-dotenv`): copy `.env.example` to `.env` and fill it in. `.env` is gitignored.
   - **Interactive prompt**: if neither of the above is set, the API notebooks fall back to `getpass.getpass()` and will prompt you at run time.

   Never commit API keys. `.gitignore` excludes `.env`, `*.key`, and `*_api_key*`, and CI runs a secret scan on every push.

## Tutorials

#### Python
* Joining POI datasets with Placekey: [[tutorial](https://www.placekey.io/blog/joining-overture-and-npi-datasets)], [[colab notebook](https://colab.research.google.com/drive/17BimmoiW4bqpyBb0-MdK2z9MwcSVAb-8?usp=sharing)]
* Joining POI and non-POI datasets with Placekey: [[tutorial](https://www.placekey.io/tutorials/joining-poi-and-non-poi-datasets-with-placekey)], [[colab notebook](https://colab.research.google.com/drive/1meH81cvoMx1IxvQ7GCVKSkW1bJM2d-DV)]
* How to Clean and Deduplicate Addresses ("De-Duping"): [[tutorial](https://www.placekey.io/tutorials/cleaning-duplicate-addresses-using-placekey)], [[colab notebook](https://colab.research.google.com/drive/178QyBsAH1quI57fxoG5yDT-IJ3RIhOoZ)]

#### Google Sheets with [Placekey for Google Sheets](https://workspace.google.com/marketplace/app/placekey_geocoder_and_address_parser/395020363939)
* Using Placekey without Addresses (Latitude and Longitude Only): [[tutorial](https://www.placekey.io/tutorials/using-placekey-without-addresses-latitude-and-longitude-only)]
* Using Placekey to Deal with Multiple Points of Interest at a Single Address: [[tutorial](https://www.placekey.io/tutorials/accounts-for-multiple-points-of-interest-at-a-single-address)]

#### ArcGIS with [AGS_placekey](https://github.com/riccardoklinger/AGS_placekey)
* Address Matching without a Geocoder: [[tutorial](https://www.placekey.io/tutorials/address-matching-without-a-geocoder)]

##  Using the [placekey-py](https://github.com/Placekey/placekey-py) Python library
#### Placekey API Utilities in `placekey-py`
* Calling Single Placekey Endpoint: [[notebook](notebooks/Placekey_py_Simple_Getting_Started_Single.ipynb)], [[colab notebook](https://colab.research.google.com/drive/1Uap9so3Es2PUo1mNaTswYqKmgD41Rebh?usp=sharing)]
* Calling Bulk Placekey Endpoint: [[notebook](notebooks/Placekey_py_Simple_Getting_Started_Bulk.ipynb)], [[colab notebook](https://colab.research.google.com/drive/1y_81Kb-j1XXTxLP4B_LJXBZp2YoFJDHr?usp=sharing)]


#### Spatial Tooling for Placekey in `placekey-py`
* Basic Spatial Functionality of Placekey: [[notebook](notebooks/basic_functionality.ipynb)]
* Advanced Spatial Functionality of Placekey: [[notebook](notebooks/advanced_functionality.ipynb)]

## Security

- API keys are read from `PLACEKEY_API_KEY` or prompted interactively — never hardcode them in cells.
- Runtime dependency versions live in `pyproject.toml`, pinned exactly; CI tool versions are ranges in the workflow files. Dependabot opens bump PRs daily, and `deps-audit.yml` runs `pip-audit` over the resolved dependency tree on every change to the manifest and weekly on a schedule.
- CI runs on every push and pull request:
  - `gitleaks` — secret scanning
  - Notebook hygiene check — blocks committed personal paths (`/Users/`, `/home/`) and API-key literals in cell sources
  - `nbmake` — executes all six notebooks: `basic_functionality` and `advanced_functionality` need no key; `Placekey_py_Simple_Getting_Started_Single`, `Placekey_py_Simple_Getting_Started_Bulk`, `Tutorial_2_Joining_POI_and_non_POI_datasets_with_Placekey` and `Adding_Placekey_to_your_POI_dataset_using_python_and_the_Placekey_API` run in a separate job that is skipped, not failed, when `PLACEKEY_API_KEY` is unavailable (a fork pull request, for instance)

If you find a security issue, please open a private report via [GitHub Security Advisories](https://github.com/Placekey/placekey-notebooks/security/advisories/new).
