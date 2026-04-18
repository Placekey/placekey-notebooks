# placekey-notebooks
This repository includes tutorials, such as Jupyter notebooks, Google Sheets guides and more, showcasing the features of the [Placekey](https://placekey.io), the [Placekey API](https://docs.placekey.io/), [Placekey Python library](https://github.com/Placekey/placekey-py) and an expanse of no-code tools.

For more details about Placekey, visit the [Placekey website](https://placekey.io/).

## Setup

1. Clone this repo and install dependencies. `requirements.txt` is **hash-pinned** (all transitive deps locked with sha256 hashes) and generated from `requirements.in`. Pip verifies hashes automatically:

   ```bash
   pip install -r requirements.txt
   ```

   To bump versions, edit `requirements.in` then regenerate:

   ```bash
   pip install "pip-tools>=7.4,<8"
   pip-compile --generate-hashes --resolver=backtracking --allow-unsafe \
       --output-file=requirements.txt requirements.in
   ```

   Dependabot also raises weekly PRs to update pinned versions + hashes (see `.github/dependabot.yml`).

2. Get a Placekey API key: [dev.placekey.io/default/register](https://dev.placekey.io/default/register).

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
- Dependencies in `requirements.txt` are hash-pinned (sha256) and verified by pip on install. Range specs live in `requirements.in`; Dependabot opens weekly bump PRs.
- CI runs on every push and pull request:
  - `gitleaks` — secret scanning
  - Notebook hygiene check — blocks committed personal paths (`/Users/`, `/home/`) and API-key literals in cell sources
  - `nbmake` — executes the key-free notebooks (`basic_functionality`, `advanced_functionality`)

If you find a security issue, please open a private report via [GitHub Security Advisories](https://github.com/Placekey/placekey-notebooks/security/advisories/new).
