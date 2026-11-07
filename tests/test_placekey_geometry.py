"""Value-pinned regression tests for the placekey-py geometry the notebooks use.

WHY THIS FILE EXISTS
--------------------
`pyproject.toml` pins all twelve dependencies with `==` and there is no
lockfile, so Dependabot proposes every bump and CI is the only thing deciding
whether it lands. The other half of CI, `nbmake`, asserts only that no notebook
cell RAISED: a bump that silently returns a different placekey, a different H3
cell, or that flips a coordinate order would go green. This file asserts the
values instead.

PROVENANCE OF THE EXPECTED VALUES
---------------------------------
Every literal below is a captured output of a cell in
`notebooks/basic_functionality.ipynb` — the notebook CI executes on every run —
not a recalled or hand-computed number. `SF_HEX_AREA_SQ_DEG` is the only
derived value: it is the shoelace area of `SF_HEX_BOUNDARY`, and it is noted as
such at its definition.

To re-capture after an intentional upstream change, run the notebook and copy
the cell outputs; do not edit a literal to make a test pass without first
establishing that the new value is correct.
"""
from __future__ import annotations

import math

import h3
import placekey as pk

SF_CITY_HALL = (37.779351, -122.418655)  # front door, per basic_functionality cell 6
SF_CITY_HALL_PLACEKEY = "@5vg-7gq-tjv"
SF_CITY_HALL_H3 = "8a2830828747fff"
SF_CITY_HALL_H3_INT = 622203769592250367
SF_CITY_HALL_H3_RESOLUTION = 10

# basic_functionality cell 6 output.
SF_CITY_HALL_CENTROID = (37.77988951810222, -122.41864762076004)

# basic_functionality cell 12 output: placekey_to_hex_boundary(), (lat, lon),
# in the order the library returned them. The ORDER is part of what is pinned.
SF_HEX_BOUNDARY = (
    (37.77921928451977, -122.41844077039543),
    (37.77972548542876, -122.41780166521563),
    (37.78039571852498, -122.41800851332172),
    (37.780559746916104, -122.41885447351558),
    (37.78005354361958, -122.41949357434298),
    (37.77938331431949, -122.41928671932915),
)

# The one derived constant: the shoelace area of SF_HEX_BOUNDARY in square
# degrees. Computed from the captured vertices above, not measured from the
# library. It is invariant under swapping the two axes, which is what makes it
# usable against placekey_to_polygon() without first knowing that function's
# coordinate order.
#
# CORRECTED: this read 1.599167262611445e-06, which was not the area of these
# vertices — it was the output of _shoelace() below before that function shifted
# its origin, wrong in the 7th significant figure through floating-point
# cancellation (see that function). The value here is the exact area of the
# SF_HEX_BOUNDARY doubles, computed in rationals; the fixed _shoelace()
# reproduces it bit for bit, and shapely's Polygon.area agrees to 2.3e-11.
SF_HEX_AREA_SQ_DEG = 1.5991663996574022e-06

# A full `what@where` placekey. basic_functionality and advanced_functionality
# both assert this form is valid; Tutorial_2 slices it (see the join test).
SF_CITY_HALL_FULL_PLACEKEY = "223-227@5vg-7gq-tjv"

# Two neighboring placekeys, from advanced_functionality cell 21.
NEIGHBOR_A = "@5vg-7gq-dn5"
NEIGHBOR_B = "@5vg-7gq-t9z"

# TOLERANCE POLICY, applied throughout.
#   * Identifiers (placekeys, H3 strings, H3 integers, booleans, lengths,
#     orderings) are compared with `==`. They are discrete; there is no
#     floating-point slack to allow and allowing any would hide a real change.
#   * Coordinates are compared with abs_tol=1e-9 degrees (~0.1 mm). That is far
#     below any geometric change the library could make and far above the
#     last-bit variation between platforms and C math library versions.
#     (An earlier version of this note called 1e-9 "the floor imposed by
#     placekey_to_wkt()". It is not: that function prints ~16 significant
#     digits, a floor of ~1e-13 degrees. 1e-9 is the platform-variation
#     allowance and nothing else constrains it.)
#   * A quantity DERIVED from those coordinates cannot be asserted tighter than
#     the coordinate tolerance allows it to move. See AREA_REL_TOL.
COORD_ABS_TOL = 1e-9

# Hexagon circumradius in degrees (~8.6e-4), measured from the pinned vertices
# rather than stated, so it cannot drift away from them.
_VERTEX_MEAN = (
    sum(p[0] for p in SF_HEX_BOUNDARY) / len(SF_HEX_BOUNDARY),
    sum(p[1] for p in SF_HEX_BOUNDARY) / len(SF_HEX_BOUNDARY),
)
SF_HEX_CIRCUMRADIUS_DEG = max(
    ((p[0] - _VERTEX_MEAN[0]) ** 2 + (p[1] - _VERTEX_MEAN[1]) ** 2) ** 0.5
    for p in SF_HEX_BOUNDARY
)

# Area tolerance, DERIVED from COORD_ABS_TOL, not chosen. Displacing all six
# vertices radially by d scales the area by (1 + d/R)**2, so an area can move by
# 2*d/R while every vertex still passes at abs_tol=d. With d=1e-9 and R=8.6e-4
# that is 2.3e-06 — the floor for any area assertion in this file. Anything
# tighter asserts more about the area than the file asserts about the vertices
# the area is computed from, which is the defect this replaced.
AREA_REL_TOL = 2 * COORD_ABS_TOL / SF_HEX_CIRCUMRADIUS_DEG


def _normalize_lat_lon(pair):
    """Return (lat, lon) regardless of which order `pair` arrived in.

    Unambiguous for this fixture: latitude 37.x is a valid latitude and
    longitude -122.x is not, so the component with |v| <= 90 is the latitude.
    Used where a function's axis order is not itself the thing under test.
    """
    a, b = pair
    return (a, b) if abs(a) <= 90 else (b, a)


def _shoelace(points) -> float:
    """Shoelace area, with the origin shifted to the first vertex.

    The shift is not cosmetic. These coordinates are ~1.2e2 while the area is
    ~1.6e-6, so the raw cross products are ~4.6e3 and a sum without that shift
    loses about nine decimal digits to cancellation. On SF_HEX_BOUNDARY that
    form returned 1.599167262611445e-06 where the exact area of the same
    doubles is 1.5991663996574022e-06 — a 5.4e-07 relative error, and the
    entire reason this file's area assertion disagreed with shapely. Shifting
    first makes the products ~1e-6 and the result exact to the last bit.
    """
    x0, y0 = points[0]
    total = 0.0
    n = len(points)
    for i in range(n):
        x1, y1 = points[i][0] - x0, points[i][1] - y0
        x2, y2 = points[(i + 1) % n][0] - x0, points[(i + 1) % n][1] - y0
        total += x1 * y2 - x2 * y1
    return abs(total) / 2


def _coords_close(got, want, tol=COORD_ABS_TOL) -> bool:
    return math.isclose(got[0], want[0], abs_tol=tol) and math.isclose(got[1], want[1], abs_tol=tol)


def _haversine_m(a, b) -> float:
    """Great-circle distance in metres on a sphere of mean Earth radius."""
    radius = 6371008.8  # mean Earth radius, metres
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    return 2 * radius * math.asin(math.sqrt(h))


# --------------------------------------------------------------------------
# Centroid and hexagon vertices
# --------------------------------------------------------------------------


def test_placekey_to_geo_returns_the_exact_centroid():
    # test_placekey_smoke.py allows 1e-3 degrees here: 111 m of latitude, 88 m
    # of longitude at 37.8N. Adjacent resolution-10 cell centroids are ~135 m
    # apart (circumradius 77.7 m, measured from SF_HEX_BOUNDARY above), so that
    # tolerance is most of a whole cell wide and detects no sub-cell movement
    # at all. Pin the captured centroid at the float-noise floor instead —
    # 1e-9 degrees is 0.11 mm.
    lat, lon = pk.placekey_to_geo(SF_CITY_HALL_PLACEKEY)
    assert _coords_close((lat, lon), SF_CITY_HALL_CENTROID)


def test_hex_boundary_vertices_and_order_are_exact():
    # Both the coordinates and their SEQUENCE are asserted. advanced_functionality
    # feeds this tuple straight into folium.Polygon(locations=...), and
    # Tutorial_2 builds WKT from the same grid, so a reordering would redraw
    # and re-join everything without raising anywhere.
    boundary = pk.placekey_to_hex_boundary(SF_CITY_HALL_PLACEKEY)
    assert len(boundary) == len(SF_HEX_BOUNDARY)
    for got, want in zip(boundary, SF_HEX_BOUNDARY, strict=True):
        assert _coords_close(got, want), f"vertex moved: {got} != {want}"


def test_centroid_is_the_mean_of_the_hexagon_vertices():
    # Cross-checks two independent entry points against each other: if a bump
    # moved the cell, both move together and the pinned values above catch it;
    # if a bump moved only one, this catches it. 1e-6 degrees (~0.1 m) because
    # the vertex mean is not defined to be the exact H3 centroid — the captured
    # values differ at the 3e-9 level.
    lat, lon = pk.placekey_to_geo(SF_CITY_HALL_PLACEKEY)
    mean_lat = sum(p[0] for p in SF_HEX_BOUNDARY) / len(SF_HEX_BOUNDARY)
    mean_lon = sum(p[1] for p in SF_HEX_BOUNDARY) / len(SF_HEX_BOUNDARY)
    assert math.isclose(lat, mean_lat, abs_tol=1e-6)
    assert math.isclose(lon, mean_lon, abs_tol=1e-6)


# --------------------------------------------------------------------------
# Coordinate order. The highest-value assertions in this file.
# --------------------------------------------------------------------------


def test_wkt_ring_is_lat_lon_ordered_and_reverse_wound():
    """placekey_to_wkt emits "lat lon" and winds opposite to hex_boundary.

    That is NOT the OGC/GeoJSON convention, and Tutorial_2 depends on it:
    cell 48 writes `placekey_to_wkt` into a `geometry` column and cell 50 feeds
    it back to `wkt_to_placekeys`. If an upstream release "corrected" the axis
    order or the winding, every placekey produced by that notebook's adjacency
    join would move to the other side of the planet — silently, because
    nothing raises. This is exactly the class of regression nbmake cannot see.
    """
    wkt = pk.placekey_to_wkt(SF_CITY_HALL_PLACEKEY)
    assert wkt.startswith("POLYGON ((") and wkt.endswith("))")
    ring = [tuple(float(v) for v in p.split()) for p in wkt[len("POLYGON ((") : -2].split(", ")]

    # Closed ring: 6 vertices plus the repeated first.
    assert len(ring) == 7
    assert _coords_close(ring[0], ring[-1])

    # First vertex is hex_boundary[0]; the remainder runs backwards.
    expected = [SF_HEX_BOUNDARY[0], *reversed(SF_HEX_BOUNDARY[1:]), SF_HEX_BOUNDARY[0]]
    for got, want in zip(ring, expected, strict=True):
        assert _coords_close(got, want), f"WKT ring changed: {got} != {want}"

    # Stated separately so a failure says which property broke: the first
    # component really is the latitude.
    assert all(abs(lat) <= 90 for lat, _ in ring)
    assert all(lon < -100 for _, lon in ring)


def test_geojson_ring_is_lon_lat_ordered_same_winding_and_closed():
    """placekey_to_geojson is the mirror image of placekey_to_wkt: (lon, lat),
    same winding as hex_boundary, ring closed. Pinning both sides is what makes
    the asymmetry above a deliberate, checked fact rather than an accident.
    """
    gj = pk.placekey_to_geojson(SF_CITY_HALL_PLACEKEY)
    # placekey-py changed this return type between minor versions: older
    # releases returned a GeoJSON mapping, newer ones a Shapely geometry
    # exposing __geo_interface__. Accept either, then assert on the mapping.
    if hasattr(gj, "__geo_interface__"):
        gj = gj.__geo_interface__
    assert gj["type"] == "Polygon"
    assert len(gj["coordinates"]) == 1
    ring = list(gj["coordinates"][0])

    assert len(ring) == 7
    assert _coords_close(ring[0], ring[-1])

    expected = [(lon, lat) for lat, lon in SF_HEX_BOUNDARY]
    expected.append(expected[0])
    for got, want in zip(ring, expected, strict=True):
        assert _coords_close(got, want), f"GeoJSON ring changed: {got} != {want}"

    assert all(lon < -100 for lon, _ in ring)
    assert all(abs(lat) <= 90 for _, lat in ring)


def test_polygon_area_and_vertices_match_the_hex_boundary():
    # placekey_to_polygon's axis order is not asserted here — the two functions
    # above already pin the orders that the notebooks consume. What matters for
    # this one is that it describes the SAME hexagon, so the comparison is made
    # axis-order-agnostic: area is invariant under a swap, and the vertex set is
    # normalized before comparison.
    #
    # AREA_REL_TOL (2.3e-06) rather than a chosen number: the area is derived
    # from vertices this file only pins to 1e-9 degrees, so that is the tightest
    # the area can honestly be held. It is still four orders of magnitude inside
    # the several-percent move any real change to the cell would produce, and
    # shapely currently lands 2.3e-11 away, leaving ~1e5 of margin. The vertex
    # comparison below is the strict check; this one is the cheap,
    # axis-order-agnostic probe that gets there first.
    poly = pk.placekey_to_polygon(SF_CITY_HALL_PLACEKEY)
    assert math.isclose(poly.area, SF_HEX_AREA_SQ_DEG, rel_tol=AREA_REL_TOL)
    assert math.isclose(_shoelace(SF_HEX_BOUNDARY), SF_HEX_AREA_SQ_DEG, rel_tol=1e-12)

    got = sorted(_normalize_lat_lon(c) for c in list(poly.exterior.coords)[:-1])
    want = sorted(SF_HEX_BOUNDARY)
    assert len(got) == 6
    for g, w in zip(got, want, strict=True):
        assert _coords_close(g, w), f"polygon vertex moved: {g} != {w}"


# --------------------------------------------------------------------------
# H3 <-> placekey, both directions
# --------------------------------------------------------------------------


def test_h3_to_placekey_round_trip():
    # Only the placekey -> H3 direction is covered by the smoke tests, but the
    # grid is the whole basis of the join in Tutorial_2 and the covering in
    # advanced_functionality. Both directions, string and integer.
    assert pk.h3_to_placekey(SF_CITY_HALL_H3) == SF_CITY_HALL_PLACEKEY
    assert pk.h3_int_to_placekey(SF_CITY_HALL_H3_INT) == SF_CITY_HALL_PLACEKEY
    assert pk.placekey_to_h3(SF_CITY_HALL_PLACEKEY) == SF_CITY_HALL_H3
    assert pk.placekey_to_h3_int(SF_CITY_HALL_PLACEKEY) == SF_CITY_HALL_H3_INT


def test_h3_int_is_the_h3_string_read_as_hexadecimal():
    # Pins the integer encoding itself rather than one captured pair, so a
    # change to how h3 packs a cell id is caught for every cell, not just this
    # one. Exact equality: these are identifiers.
    assert int(SF_CITY_HALL_H3, 16) == SF_CITY_HALL_H3_INT
    assert int(pk.placekey_to_h3(SF_CITY_HALL_PLACEKEY), 16) == pk.placekey_to_h3_int(
        SF_CITY_HALL_PLACEKEY
    )


def test_placekey_grid_is_h3_resolution_10():
    # basic_functionality cell 9 prints this. If placekey-py or h3 ever moved
    # the grid resolution, cell sizes change by ~7x and every join in these
    # notebooks changes meaning while still running clean.
    assert h3.get_resolution(SF_CITY_HALL_H3) == SF_CITY_HALL_H3_RESOLUTION
    assert h3.get_resolution(pk.placekey_to_h3(SF_CITY_HALL_PLACEKEY)) == SF_CITY_HALL_H3_RESOLUTION


def test_geo_to_placekey_agrees_with_h3_directly():
    # Crosses the pinned pair over the h3 dependency: placekey==0.0.36 and
    # h3==4.4.2 are bumped independently by Dependabot, and this is the
    # assertion that fails if they drift apart.
    cell = h3.latlng_to_cell(SF_CITY_HALL[0], SF_CITY_HALL[1], SF_CITY_HALL_H3_RESOLUTION)
    assert cell == SF_CITY_HALL_H3
    assert pk.h3_to_placekey(cell) == pk.geo_to_placekey(*SF_CITY_HALL)
    assert pk.geo_to_placekey(*SF_CITY_HALL) == SF_CITY_HALL_PLACEKEY


def test_what_part_is_ignored_by_the_where_lookups():
    # Tutorial_2 cells 31 and 43 split a `what@where` placekey with the literal
    # slices [7:] and [0:11] and join on the result. Those magic numbers are
    # only correct while the `what` part of a full placekey is 7 characters.
    assert SF_CITY_HALL_FULL_PLACEKEY[7:] == SF_CITY_HALL_PLACEKEY
    assert SF_CITY_HALL_PLACEKEY[0:11] == "@5vg-7gq-tj"
    assert pk.placekey_format_is_valid(SF_CITY_HALL_FULL_PLACEKEY)

    # And the library must agree that the `what` part does not move the cell.
    assert pk.placekey_to_h3(SF_CITY_HALL_FULL_PLACEKEY) == SF_CITY_HALL_H3
    assert pk.placekey_to_geo(SF_CITY_HALL_FULL_PLACEKEY) == pk.placekey_to_geo(
        SF_CITY_HALL_PLACEKEY
    )


# --------------------------------------------------------------------------
# Distance
# --------------------------------------------------------------------------


def test_placekey_distance_is_metres_between_the_two_centroids():
    """Pin the UNIT and the FORMULA, not a captured number.

    test_placekey_smoke.py asserts only `0 < d < 1000`, which a change from
    metres to kilometers, or to a planar approximation, would survive. The
    distance is recomputed here from `placekey_to_geo` — itself pinned above —
    with a haversine written out in full.

    rel_tol=1e-2 because the Earth-radius constant and the choice of haversine
    versus an ellipsoidal geodesic legitimately differ by a few tenths of a
    percent between implementations. 1% is tight enough to catch a unit change
    (a factor of 1000) or a projection change, and loose enough not to fail on
    a constant.
    """
    a = pk.placekey_to_geo(NEIGHBOR_A)
    b = pk.placekey_to_geo(NEIGHBOR_B)
    got = pk.placekey_distance(NEIGHBOR_A, NEIGHBOR_B)
    assert math.isclose(got, _haversine_m(a, b), rel_tol=1e-2)


def test_placekey_distance_identity_and_symmetry():
    # Exact equality on both: the identity is 0 by construction and symmetry is
    # a property of the formula, so any slack here would only hide a defect.
    assert pk.placekey_distance(SF_CITY_HALL_PLACEKEY, SF_CITY_HALL_PLACEKEY) == 0
    assert pk.placekey_distance(NEIGHBOR_A, NEIGHBOR_B) == pk.placekey_distance(
        NEIGHBOR_B, NEIGHBOR_A
    )


def test_prefix_distance_dict_bounds_a_real_pair():
    # advanced_functionality cell 23 prints this table but nothing checks that
    # it agrees with placekey_distance. The two placekeys share the `5vg-7gq`
    # prefix, so the table's bound for a shared prefix of that length must be
    # an upper bound on their measured separation. Crossing the two APIs is the
    # point; neither number is hardcoded.
    table = pk.get_prefix_distance_dict()
    shared = 0
    for ca, cb in zip(NEIGHBOR_A[1:], NEIGHBOR_B[1:], strict=True):
        if ca != cb:
            break
        shared += 1
    # Count only the alphanumeric characters of the shared prefix: the table is
    # keyed by `where` characters and the dashes are formatting. The exact key
    # convention is read off the table rather than assumed, so this stays a
    # real cross-check if upstream renumbers the keys: take the longest key
    # that is no longer than the prefix the two keys actually share.
    shared_chars = len([c for c in NEIGHBOR_A[1 : 1 + shared] if c != "-"])
    applicable = [k for k in table if k <= shared_chars]
    assert applicable, f"prefix distance table has no key <= {shared_chars}: {sorted(table)}"
    assert pk.placekey_distance(NEIGHBOR_A, NEIGHBOR_B) <= table[max(applicable)]


# --------------------------------------------------------------------------
# wkt_to_placekeys: the Tutorial_2 adjacency round trip
# --------------------------------------------------------------------------


def test_wkt_to_placekeys_round_trips_the_originating_cell():
    """Tutorial_2 cell 50 calls this on a WKT it built with placekey_to_wkt.

    The cell a hexagon came from must be in the cover of that hexagon. That is
    true by construction, which is what makes it a good probe: it is the single
    assertion that fails if the axis order of either function changes, and it
    needs no captured value to state.
    """
    wkt = pk.placekey_to_wkt(SF_CITY_HALL_PLACEKEY)
    cover = pk.wkt_to_placekeys(wkt, include_touching=True)
    found = set(cover["interior"]) | set(cover["boundary"])
    assert SF_CITY_HALL_PLACEKEY in found

    # Everything returned is a real placekey on the same grid.
    for key in found:
        assert pk.placekey_format_is_valid(key)
        assert h3.get_resolution(pk.placekey_to_h3(key)) == SF_CITY_HALL_H3_RESOLUTION


def test_include_touching_widens_the_cover():
    # A definitional property, so exact set containment rather than a count:
    # pinning a count would break on a float tie at a hexagon edge, which is
    # not a regression.
    wkt = pk.placekey_to_wkt(SF_CITY_HALL_PLACEKEY)
    tight = pk.wkt_to_placekeys(wkt, include_touching=False)
    wide = pk.wkt_to_placekeys(wkt, include_touching=True)
    tight_set = set(tight["interior"]) | set(tight["boundary"])
    wide_set = set(wide["interior"]) | set(wide["boundary"])
    assert tight_set <= wide_set
    assert SF_CITY_HALL_PLACEKEY in tight_set
