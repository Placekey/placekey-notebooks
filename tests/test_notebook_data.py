"""Value-pinned tests for the committed data the notebooks read, and for the
dataframe operations they perform on it.

`test_data_integrity.py` already pins the BYTES of the committed shapefile
against a SHA256 manifest. That catches a corrupted file; it says nothing about
whether the current geopandas/pyogrio/shapely stack still READS those bytes the
same way. With every dependency pinned by `==` and no lockfile, a geopandas or
shapely bump reaches CI with nothing but these tests between it and `main`.

So the assertions here are deliberately on the far side of the parser: the
feature count, the column set, the coordinate-reference frame, and the bounding
boxes in degrees. All of them were read out of the shapefile's own binary
headers (the .shp record headers and the .dbf field descriptors) rather than
from a geopandas run, so they are properties of the FILE and the parser must
reproduce them.
"""
from __future__ import annotations

import ast
import json
import math
import pathlib

import geopandas as gpd
import pandas as pd
import placekey as pk
import pytest
from shapely.geometry import Point

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
CBG_DIR = DATA_DIR / "CA_2019_census_block_groups_sample"
POI_FIXTURE = DATA_DIR / "my_places_data_missing.csv"
BULK_FIXTURE = DATA_DIR / "bulk_sample_places.csv"
BULK_NOTEBOOK = REPO_ROOT / "notebooks" / "Placekey_py_Simple_Getting_Started_Bulk.ipynb"


def notebook_dict_literal(notebook: pathlib.Path, name: str) -> dict:
    """Return the dict literal assigned to `name` in a notebook's code cells.

    READ from the notebook rather than copied into this file. A copy would
    pass after someone renamed a key in the notebook — which is the "fixture
    that passes for the wrong reason" shape this file exists to avoid.

    Only usable where the literal is made entirely of constants. The sibling
    notebook's map is not: it keys off a variable (`query_id_col`), so that
    one is checked by column name below instead.
    """
    nb = json.loads(notebook.read_text(encoding="utf-8"))
    for cell in nb["cells"]:
        if cell["cell_type"] != "code":
            continue
        try:
            tree = ast.parse("".join(cell["source"]))
        except SyntaxError:
            continue  # cells carrying IPython escapes are not plain Python
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == name for t in node.targets
            ):
                return ast.literal_eval(node.value)
    raise AssertionError(f"no literal assignment to `{name}` in {notebook.name}")

# --- values read from the shapefile's own headers -------------------------
# .dbf header: 581 records, 12 character/numeric field descriptors.
CBG_FEATURE_COUNT = 581
CBG_COLUMNS = (
    "GEOID",
    "STATEFP",
    "COUNTYFP",
    "TRACTCE",
    "BLKGRPCE",
    "NAMELSAD",
    "MTFCC",
    "FUNCSTAT",
    "ALAND",
    "AWATER",
    "INTPTLAT",
    "INTPTLON",
)
# .shp main header, bytes 36..68: min X, min Y, max X, max Y.
CBG_TOTAL_BOUNDS = (-123.173825, 37.63983, -122.28178, 37.929824)

# The single block group advanced_functionality cell 9 selects, and its own
# record bounding box from the .shp record header (one part, 26 points).
TARGET_GEOID = "060750124022"
TARGET_BOUNDS = (-122.420689, 37.77521, -122.416292, 37.782379)
TARGET_RING_POINTS = 26

# Bounds are printed into the shapefile at float64 precision and reproduced by
# the parser; 1e-9 degrees (~0.1 mm) is float noise, not a geometric allowance.
BOUNDS_ABS_TOL = 1e-9

# A resolution-10 H3 cell is roughly 0.0015 degrees across at this latitude.
# Used only to bound how far a covering hexagon may stick out of the polygon it
# covers; it is a geometric fact about the grid, not a tuning knob.
HEX_SPAN_DEG = 0.002


@pytest.fixture(scope="module")
def cbgs() -> gpd.GeoDataFrame:
    return gpd.read_file(CBG_DIR).set_index("GEOID")


# --------------------------------------------------------------------------
# The shapefile, as the current stack parses it
# --------------------------------------------------------------------------


def test_shapefile_feature_count_and_columns(cbgs):
    # Exact equality on both: a dropped feature or a renamed attribute column
    # is never a rounding artifact. GEOID becomes the index, so it is excluded.
    assert len(cbgs) == CBG_FEATURE_COUNT
    assert set(cbgs.columns) == set(CBG_COLUMNS[1:]) | {"geometry"}
    assert cbgs.index.name == "GEOID"
    assert cbgs.index.is_unique


def test_shapefile_is_read_in_geographic_degrees(cbgs):
    # The EPSG code is NOT asserted: the .prj carries ESRI-flavoured WKT
    # ("GCS_North_American_1983") with no AUTHORITY node, so whether GDAL
    # resolves it to EPSG:4269 is a property of the GDAL build, not of this
    # repository, and pinning it would make an unrelated system upgrade look
    # like a data defect. What the notebooks actually depend on is that the
    # coordinates arrive as lat/lon degrees — which the bounds below prove far
    # more directly than a code would.
    assert cbgs.crs is not None
    assert cbgs.crs.is_geographic

    got = tuple(cbgs.total_bounds)
    for g, w in zip(got, CBG_TOTAL_BOUNDS, strict=True):
        assert math.isclose(g, w, abs_tol=BOUNDS_ABS_TOL), f"total_bounds moved: {got}"


def test_target_block_group_geometry(cbgs):
    # advanced_functionality cell 9 hardcodes this GEOID. If it ever stopped
    # resolving, that notebook would raise and nbmake would catch it — but a
    # geometry that silently CHANGED (an axis swap on read, a ring dropped)
    # would not, and every placekey derived from it downstream would move.
    assert TARGET_GEOID in cbgs.index
    geom = cbgs.loc[TARGET_GEOID]["geometry"]
    assert geom.geom_type == "Polygon"
    assert geom.is_valid

    for g, w in zip(geom.bounds, TARGET_BOUNDS, strict=True):
        assert math.isclose(g, w, abs_tol=BOUNDS_ABS_TOL), f"bounds moved: {geom.bounds}"

    # The .shp record header declares 1 part and 26 points; shapely keeps the
    # closing point, so the exterior ring has the same 26 coordinates.
    assert len(geom.interiors) == 0
    assert len(geom.exterior.coords) == TARGET_RING_POINTS

    # Shapefile polygon coordinates are (x, y) = (lon, lat). Asserting the
    # axis order explicitly because the covering call below depends on it.
    longitudes = [c[0] for c in geom.exterior.coords]
    latitudes = [c[1] for c in geom.exterior.coords]
    assert all(lon < -100 for lon in longitudes)
    assert all(30 < lat < 45 for lat in latitudes)


# --------------------------------------------------------------------------
# polygon_to_placekeys over that geometry — advanced_functionality cell 13
# --------------------------------------------------------------------------


def test_polygon_to_placekeys_covers_the_block_group(cbgs):
    """The cover is asserted by its geometric properties, not by a pinned list.

    A list of covering placekeys would be the stronger test, but it cannot be
    produced here without running the pinned stack, and a hand-written one
    would be a guess. What can still be asserted without one, and still catches the
    failure that matters, is the relationship between the cover and the
    polygon: an axis swap in either `polygon_to_placekeys` or the shapefile
    reader moves every hexagon off the block group entirely, and a resolution
    change breaks the containment bound.
    """
    geom = cbgs.loc[TARGET_GEOID]["geometry"]
    cover = pk.polygon_to_placekeys(geom, geo_json=True)

    assert set(cover) >= {"interior", "boundary"}
    interior = list(cover["interior"])
    boundary = list(cover["boundary"])
    assert interior, "no interior hexagons returned for a block group this size"
    assert boundary, "no boundary hexagons returned"

    # A hexagon is either wholly inside or on the edge, never both.
    assert not (set(interior) & set(boundary))

    min_lon, min_lat, max_lon, max_lat = geom.bounds
    for key in interior + boundary:
        assert pk.placekey_format_is_valid(key)
        lat, lon = pk.placekey_to_geo(key)
        # Centroids of edge hexagons may sit just outside the polygon, but no
        # further out than one cell. This is what fails loudly on an axis swap.
        assert min_lat - HEX_SPAN_DEG <= lat <= max_lat + HEX_SPAN_DEG, f"{key} latitude outside"
        assert min_lon - HEX_SPAN_DEG <= lon <= max_lon + HEX_SPAN_DEG, f"{key} longitude outside"

    # Interior cells must sit inside the polygon, and every returned cell must
    # touch it. Stated on centroids and on intersection rather than on full
    # polygon containment: `interior` is h3's polyfill minus the cells crossing
    # the ring, so a cell exactly tangent to the ring is a legitimate edge case
    # and not a regression. An axis swap, a resolution change or a dropped
    # ring all still fail here, because the cover would stop meeting the
    # polygon at all. geo_json=True puts the hexagon in (lon, lat), the same
    # order as the shapefile geometry, so the two are directly comparable.
    for key in interior:
        lat, lon = pk.placekey_to_geo(key)
        assert geom.contains(Point(lon, lat)), f"{key} centroid is outside the block group"

    for key in interior + boundary:
        hexagon = pk.placekey_to_polygon(key, geo_json=True)
        assert geom.intersects(hexagon), f"{key} does not touch the block group"


# --------------------------------------------------------------------------
# The committed POI fixture
# --------------------------------------------------------------------------


def test_poi_fixture_shape_and_dtypes():
    """Pins the fixture that unblocks
    notebooks/Adding_Placekey_to_your_POI_dataset_using_python_and_the_Placekey_API.ipynb.

    That notebook reads `../data/my_places_data_missing.csv` with a nine-entry
    dtype map whose load-bearing entry is `zip_code: str`, so leading zeros
    survive. Only that entry is reproduced here — the rest name columns pandas
    would infer identically, and two of them (`iso_country_code`, `lat`/`lon`
    aliases) are not columns of this file at all. A pandas bump that changed
    `dtype=` handling then fails in a test that says so, rather than in a
    notebook cell forty lines later.
    """
    df = pd.read_csv(POI_FIXTURE, dtype={"zip_code": str, "internal_place_id": str})
    assert list(df.columns) == [
        "internal_place_id",
        "store_name",
        "lat",
        "lon",
        "full_address",
        "city",
        "state",
        "zip_code",
    ]
    assert df.shape == (10, 8)
    assert df["internal_place_id"].is_unique

    # The notebook is about handling absent fields, and its cell 14 prose names
    # WHICH ones — in POST-rename API terms: "some rows are missing
    # `postal_code`, `latitude`/`longitude`, and even the `street_address`".
    # The CSV carries the PRE-rename names, so cell 11's column_map is the
    # translation: zip_code -> postal_code, lat/lon -> latitude/longitude,
    # full_address -> street_address. Assert exactly those three gaps and no
    # others, so the tutorial's text and its sample data cannot drift apart.
    assert df.isnull().any(axis=1).sum() == 3
    assert df["lat"].isnull().sum() == 1
    assert df["lon"].isnull().sum() == 1
    assert df["zip_code"].isnull().sum() == 1
    assert df["full_address"].isnull().sum() == 1
    assert df["store_name"].notna().all()
    assert df["city"].notna().all()
    assert df["state"].notna().all()

    # The leading zero is the reason for the dtype map. Exact string equality.
    assert "02133" in set(df["zip_code"].dropna())
    assert df["lat"].dtype.kind == "f"


# --------------------------------------------------------------------------
# Tutorial_2's join, reproduced on a fixed frame
# --------------------------------------------------------------------------


def test_where_placekey_join_matches_on_the_where_part():
    """Tutorial_2 cells 31/35/36 join POI rows to parking-meter counts by
    slicing the `what` part off a full placekey and grouping on the remainder.

    The join is the result the notebook exists to produce, and `nbmake` would
    pass a version of it that matched nothing at all — an empty merge raises
    no error. Reproduce it on a three-row frame with a known answer.
    """
    poi_df = pd.DataFrame(
        {
            "placekey": ["223-227@5vg-7gq-tjv", "zzw-224@5vg-7gq-dn5", "222-222@5vg-7gq-t9z"],
            "location_name": ["City Hall", "Neighbor A", "Neighbor B"],
        }
    )
    meters = pd.DataFrame(
        {
            "placekey": ["@5vg-7gq-tjv", "@5vg-7gq-tjv", "@5vg-7gq-dn5"],
            "OBJECTID": ["1", "2", "3"],
        }
    )

    poi_df = poi_df.assign(where_placekey=poi_df["placekey"].str[7:])
    assert list(poi_df["where_placekey"]) == [
        "@5vg-7gq-tjv",
        "@5vg-7gq-dn5",
        "@5vg-7gq-t9z",
    ]

    counts = (
        meters.groupby("placekey")
        .agg({"OBJECTID": "count"})
        .reset_index()
        .rename({"OBJECTID": "meters"}, axis=1)
    )
    joined = counts.merge(poi_df, left_on="placekey", right_on="where_placekey", how="right")
    joined["meters"] = joined["meters"].fillna(0).astype(int)

    # Exact integers: a right join of three POI rows must stay three rows, and the
    # counts are counts. A row count or a NaN appearing here is the signature
    # of the join having stopped matching.
    assert len(joined) == 3
    got = dict(zip(joined["location_name"], joined["meters"], strict=True))
    assert got == {"City Hall": 2, "Neighbor A": 1, "Neighbor B": 0}


def test_truncated_where_prefix_join_groups_neighboring_cells():
    """Tutorial_2 cells 42/43 widen the same join by truncating the `where`
    part to 11 characters, which merges neighboring resolution-10 cells into
    a coarser bucket. Pin that the truncation really does collapse distinct
    placekeys together — if it stopped doing so the notebook's "more matches
    at lower precision" conclusion would silently become false.
    """
    fine = ["@5vg-7gq-tjv", "@5vg-7gq-tj5", "@5vg-7gq-dn5"]
    coarse = [key[0:11] for key in fine]
    assert coarse == ["@5vg-7gq-tj", "@5vg-7gq-tj", "@5vg-7gq-dn"]
    assert len(set(coarse)) == 2

    # And the full-placekey form slices to the same bucket, which is what makes
    # the two sides of the notebook's merge comparable.
    assert "223-227@5vg-7gq-tjv"[7:18] == "@5vg-7gq-tj"


def test_bulk_fixture_satisfies_the_notebooks_column_map():
    """Pins the fixture that unblocks Placekey_py_Simple_Getting_Started_Bulk.

    Its cell 7 helper selects `list(column_map.values())` after renaming, so
    every KEY of the map must be a column of this file or the notebook raises a
    KeyError. The map is parsed out of the notebook, so a rename on either side
    shows up here naming the column, not as a notebook traceback in CI.
    """
    column_map = notebook_dict_literal(BULK_NOTEBOOK, "column_map")
    df = pd.read_csv(BULK_FIXTURE)

    # The map read out of the notebook, not a copy of it. Rename a key in
    # cell 12 and this fails naming the column the fixture no longer has.
    missing = sorted(set(column_map) - set(df.columns))
    assert not missing, f"notebook column_map names columns the fixture lacks: {missing}"
    assert set(column_map.values()) >= {"query_id", "region", "iso_country_code"}
    assert df.shape == (10, 6)
    assert df["index"].is_unique
    assert not df.isnull().to_numpy().any(), "the bulk tutorial has no missing-data step"
    assert set(df["country_code"]) == {"US"}

    # `index` must stay a STRING. Cell 7's merge_and_format joins it against a
    # `query_id` that cell 16 reads back with dtype=str, and pandas raises
    # ValueError on an int64-to-object merge. Numeric-looking ids would be
    # inferred as int64 and break the notebook's last cell. Exact dtype check.
    assert df["index"].dtype == object
    assert not df["index"].str.fullmatch(r"\d+").any()

    # The rename the notebook performs must land on the API field names.
    renamed = df.rename(columns=column_map)
    assert set(column_map.values()).issubset(renamed.columns)
