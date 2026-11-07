"""Smoke tests for placekey-py core conversions.

These run with no API key and catch upstream placekey-py regressions that
nbmake would also catch — but faster, and without needing to execute a
full notebook. The reference values are taken from basic_functionality.ipynb
(SF City Hall = (37.779351, -122.418655)).

This file is the breadth layer and its tolerances are deliberately loose.
tests/test_placekey_geometry.py is the depth layer: it pins the exact centroid,
the hexagon vertices and their order, the coordinate order of the WKT and
GeoJSON forms, and the units of placekey_distance. Add a new value-pinned
assertion there, not here.
"""
from __future__ import annotations

import math

import placekey as pk

SF_CITY_HALL = (37.779351, -122.418655)
SF_CITY_HALL_PLACEKEY = "@5vg-7gq-tjv"
SF_CITY_HALL_H3 = "8a2830828747fff"
SF_CITY_HALL_H3_INT = 622203769592250367


def test_geo_to_placekey_sf_city_hall():
    assert pk.geo_to_placekey(*SF_CITY_HALL) == SF_CITY_HALL_PLACEKEY


def test_placekey_to_geo_round_trip():
    lat, lon = pk.placekey_to_geo(SF_CITY_HALL_PLACEKEY)
    # Loose on purpose — 1e-3 degrees is ~111 m against a ~155 m cell.
    # test_placekey_geometry.py pins the exact centroid.
    assert math.isclose(lat, SF_CITY_HALL[0], abs_tol=1e-3)
    assert math.isclose(lon, SF_CITY_HALL[1], abs_tol=1e-3)


def test_placekey_to_h3_string():
    assert pk.placekey_to_h3(SF_CITY_HALL_PLACEKEY) == SF_CITY_HALL_H3


def test_placekey_to_h3_int():
    assert pk.placekey_to_h3_int(SF_CITY_HALL_PLACEKEY) == SF_CITY_HALL_H3_INT


def test_placekey_format_validity():
    assert pk.placekey_format_is_valid(SF_CITY_HALL_PLACEKEY)
    assert pk.placekey_format_is_valid("223-227@5vg-7gq-tjv")
    assert not pk.placekey_format_is_valid("223-227@ima-bad-key")
    assert not pk.placekey_format_is_valid("not-a-placekey")


def test_placekey_to_hex_boundary_shape():
    boundary = pk.placekey_to_hex_boundary(SF_CITY_HALL_PLACEKEY)
    assert len(boundary) == 6
    for pt in boundary:
        assert len(pt) == 2
        lat, lon = pt
        assert math.isclose(lat, SF_CITY_HALL[0], abs_tol=1e-2)
        assert math.isclose(lon, SF_CITY_HALL[1], abs_tol=1e-2)


def test_placekey_to_wkt_is_polygon():
    wkt = pk.placekey_to_wkt(SF_CITY_HALL_PLACEKEY)
    assert wkt.startswith("POLYGON ((")
    assert wkt.endswith("))")


def test_placekey_to_geojson_structure():
    gj = pk.placekey_to_geojson(SF_CITY_HALL_PLACEKEY)
    # placekey-py changed this return type between minor versions:
    # older releases returned a GeoJSON dict; newer ones return a Shapely Polygon
    # exposing __geo_interface__. Accept either and assert on the resulting dict.
    if hasattr(gj, "__geo_interface__"):
        gj = gj.__geo_interface__
    assert gj["type"] == "Polygon"
    assert len(gj["coordinates"]) == 1
    ring = gj["coordinates"][0]
    assert ring[0] == ring[-1]
    assert len(ring) == 7


def test_placekey_to_polygon_is_shapely():
    from shapely.geometry.polygon import Polygon

    poly = pk.placekey_to_polygon(SF_CITY_HALL_PLACEKEY)
    assert isinstance(poly, Polygon)
    assert poly.area > 0


def test_placekey_distance_is_positive():
    # Two neighboring Placekeys from advanced_functionality.ipynb
    d = pk.placekey_distance("@5vg-7gq-dn5", "@5vg-7gq-t9z")
    assert d > 0
    assert d < 1000  # neighbors are well under 1 km apart


def test_prefix_distance_dict_monotone():
    table = pk.get_prefix_distance_dict()
    assert isinstance(table, dict)
    # Longer shared prefix ⇒ smaller max distance.
    keys = sorted(table.keys())
    values = [table[k] for k in keys]
    assert values == sorted(values, reverse=True)
