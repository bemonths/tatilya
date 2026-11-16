"""GÖREV-20: road distances and estimated driving times on the OpenStreetMap road network.

A small synthetic network through httpx.MockTransport only; suite-wide no_real_http prevents internet access.
"""
import json
import sqlite3
from datetime import date

import httpx
import pytest
from fastapi.testclient import TestClient

from studio.app import create_app
from studio.database import Database
from studio.destinations import thirty_a
from studio.sources import climate_http, road_graph
from studio.sources import road_network as rn
from studio.sources.base import SourceError
from studio.sources.geo import distance_km
from tests.legacy import V20_INTERVALS, V20_TABLES, V21_TABLES, drop_v20
from tests.test_beaches import HEADERS
from tests.test_daily_needs import answer_mock as points_mock
from tests.test_daily_needs import element
from tests.test_lodging import BookDirectMock, fast, inventory, lodging, start  # noqa: F401  (fast: autouse fixture)
from tests.test_monthly_windows import use
from studio.sources import daily_needs as dn

SETTINGS = {**thirty_a.ROAD_NETWORK, "extra_points": [{"key": "AIR", "label": "Deneme Havalimanı", "latitude": 30.3000, "longitude": -86.0400}],
            "length_checks": [{"label": "Ana yol", "refs": ["CR 1"], "expected_miles": 3.0, "source": "deneme"}]}
REAL_COLLECT = rn.collect


def node(identifier, lat, lon):
    return {"type": "node", "id": identifier, "lat": lat, "lon": lon}


def way(identifier, nodes, **tags):
    return {"type": "way", "id": identifier, "nodes": nodes, "tags": {"highway": "residential", **tags}}


# A main road west to east along 30.30 (nodes 1..6, 0.01 degrees apart), a side street north from node 2 to a store, a loop road
# north of the main road that is longer but posted faster, a private street from node 5, a closed road and a parking aisle.
NODES = [node(1, 30.30, -86.10), node(2, 30.30, -86.09), node(3, 30.30, -86.08), node(4, 30.30, -86.07), node(5, 30.30, -86.06),
         node(6, 30.30, -86.05), node(7, 30.31, -86.09), node(8, 30.32, -86.09), node(9, 30.32, -86.06), node(10, 30.31, -86.06),
         node(11, 30.29, -86.06), node(12, 30.28, -86.06), node(13, 30.29, -86.08), node(14, 30.29, -86.07), node(15, 30.30, -86.04)]
WAYS = [way(100, [1, 2, 3, 4, 5, 6, 15], highway="tertiary", ref="CR 1", maxspeed="10 mph"),
        way(101, [2, 7, 8], maxspeed="60 mph"),
        way(102, [8, 9, 10, 5], highway="primary", maxspeed="60 mph"),
        way(103, [5, 11, 12], access="private"),
        way(104, [3, 13, 14, 4], access="no"),
        way(105, [4, 14], highway="service", service="parking_aisle"),
        way(106, [13, 14], highway="footway")]
ANSWER = {"osm3s": {"timestamp_osm_base": "2026-11-16T10:00:00Z"}, "elements": NODES + WAYS}


def graph(settings=SETTINGS, answer=ANSWER):
    nodes, ways, _, stamp = road_graph.parse(json.dumps(answer).encode())
    return road_graph.build(nodes, ways, settings), stamp


def trip(g, origin, target, settings=SETTINGS):
    limit = settings["snap_limit_m"] / 1000
    a, b = g.snap(*origin, limit), g.snap(*target, limit)
    return g.trip(a, b, g.to_target(b), 1.0 / (settings["snap_speed_mph"] * rn.MILE_KM))


@pytest.fixture(autouse=True)
def no_gap(monkeypatch):
    monkeypatch.setattr(climate_http, "REQUEST_GAP", 0)


def test_graph_keeps_configured_roads_and_leaves_out_closed_skipped_and_unlisted_ways():
    g, stamp = graph()
    assert stamp == "2026-11-16T10:00:00Z" and g.way_count == 4                    # 100, 101, 102, 103; not the closed road, the aisle, the footway
    assert {s[7] for s in g.segments} == {100, 101, 102, 103}
    assert g.refs["CR 1"] == pytest.approx(distance_km(30.30, -86.10, 30.30, -86.04), rel=1e-6)
    assert g.speed_sources["maxspeed"] > 0 and g.speed_sources["default"] > 0


def test_speed_comes_from_maxspeed_else_from_the_configured_default_of_the_highway_type():
    defaults = SETTINGS["speeds_mph"]
    assert road_graph.speed_mph({"highway": "residential", "maxspeed": "35 mph"}, defaults) == (35.0, "maxspeed")
    kmh, source = road_graph.speed_mph({"highway": "residential", "maxspeed": "50"}, defaults)
    assert source == "maxspeed" and kmh == pytest.approx(50 / 1.609344)
    assert road_graph.speed_mph({"highway": "residential", "maxspeed": "signals"}, defaults) == (defaults["residential"], "default")
    assert road_graph.speed_mph({"highway": "service"}, {**defaults, "service": 7}) == (7.0, "default")     # a setting, not a constant in code


def test_road_distance_is_never_shorter_than_the_great_circle_distance():
    g, _ = graph()
    points = [(30.3004, -86.0990), (30.3195, -86.0895), (30.3102, -86.0604), (30.2996, -86.0402), (30.2905, -86.0601), (30.3001, -86.0700)]
    checked = 0
    for origin in points:
        for target in points:
            found = trip(g, origin, target)
            if found is None or origin == target:
                continue
            assert found[0] >= distance_km(*origin, *target) - 1e-9 and found[1] > 0
            checked += 1
    assert checked >= 20


def test_route_is_the_fastest_one_and_its_length_is_the_length_of_that_route():
    g, _ = graph()
    west, east = (30.30, -86.10), (30.30, -86.06)
    km, hours = trip(g, west, east)
    direct = distance_km(*west, *east)
    assert km > direct * 1.5                                    # the posted-faster loop is longer than the 10 mph main road
    slow = {**SETTINGS}
    answer = json.loads(json.dumps(ANSWER))
    next(w for w in answer["elements"] if w.get("id") == 102 and w["type"] == "way")["tags"]["maxspeed"] = "5 mph"
    g2, _ = graph(slow, answer)
    km2, hours2 = trip(g2, west, east)
    assert km2 == pytest.approx(direct, rel=1e-6) and hours2 == pytest.approx(direct / (10 * 1.609344), rel=1e-6) and hours2 > hours


def test_one_way_streets_are_followed_in_their_direction_only():
    answer = json.loads(json.dumps(ANSWER))
    next(w for w in answer["elements"] if w.get("id") == 100 and w["type"] == "way")["tags"]["oneway"] = "yes"
    next(w for w in answer["elements"] if w.get("id") == 102 and w["type"] == "way")["tags"]["oneway"] = "-1"
    g, _ = graph(answer=answer)
    there = trip(g, (30.30, -86.10), (30.30, -86.06))           # along the main road, with its direction
    back = trip(g, (30.30, -86.06), (30.30, -86.09))            # only over the loop (its reversed direction), then down the side street
    assert there[0] == pytest.approx(distance_km(30.30, -86.10, 30.30, -86.06), rel=1e-6)
    assert back[0] > distance_km(30.30, -86.06, 30.30, -86.09) * 2
    assert road_graph.directions({"highway": "motorway"}) == (True, False) and road_graph.directions({"highway": "residential", "junction": "roundabout"}) == (True, False)


def test_a_private_road_is_used_at_the_ends_of_a_trip_but_never_to_cut_through():
    answer = json.loads(json.dumps(ANSWER))
    # the private street now joins the main road at both ends (5 -> 11 -> 12 -> 15): the shortest way from 5 to 15 would cut through it
    answer["elements"].append(node(16, 30.2999, -86.0500))
    next(w for w in answer["elements"] if w.get("id") == 103 and w["type"] == "way")["nodes"] = [5, 16, 15]
    next(w for w in answer["elements"] if w.get("id") == 103 and w["type"] == "way")["tags"]["maxspeed"] = "70 mph"
    g, _ = graph(answer=answer)
    km, _ = trip(g, (30.30, -86.07), (30.30, -86.04))
    assert km == pytest.approx(distance_km(30.30, -86.07, 30.30, -86.04), rel=1e-4)       # stays on the public road
    home = (30.29995, -86.0500)                                                          # a home on the private street itself
    assert trip(g, home, (30.30, -86.10)) is not None and trip(g, (30.30, -86.10), home) is not None


def test_a_point_far_from_every_road_is_not_tied_to_the_network():
    g, _ = graph()
    assert g.snap(30.40, -86.10, 0.5) is None and g.snap(0.0, 0.0, 0.5) is None
    near = g.snap(30.3003, -86.0950, 0.5)
    assert near["leg_km"] == pytest.approx(distance_km(30.3003, -86.0950, 30.30, -86.0950), rel=1e-3)


def test_nearest_point_is_chosen_by_road_distance_not_by_straight_line():
    g, _ = graph()
    # the listing is on the main road; store A is a little nearer in a straight line but only reached over the side street and the loop,
    # store B is on the main road
    listing = {"lodging_id": 1, "latitude": 30.3001, "longitude": -86.0700}
    targets = [{"target_key": "node/a", "category_key": "market", "kind": "poi", "name": "A", "latitude": 30.3100, "longitude": -86.0690},
               {"target_key": "node/b", "category_key": "market", "kind": "poi", "name": "B", "latitude": 30.3001, "longitude": -86.0560}]
    settings = {**SETTINGS, "snap_limit_m": 1200}
    rows, targets, counts = rn.measure(g, [listing, {"lodging_id": 2, "latitude": None, "longitude": None},
                                           {"lodging_id": 3, "latitude": 0.0, "longitude": 0.0}], targets, settings)
    assert counts == {"listing_count": 3, "tied_count": 1, "measured_count": 1}
    row = rows[0]
    assert row["crow_nearest_key"] == "node/a" and row["target_key"] == "node/b"
    assert row["road_km"] >= row["crow_km"] >= row["crow_nearest_km"] and row["minutes"] > 0
    assert [t["reached_count"] for t in targets] == [1, 1] and all(t["snap_m"] is not None for t in targets)


def test_collect_asks_one_query_waits_when_the_server_is_busy_and_checks_known_lengths(tmp_path):
    with pytest.raises(SourceError, match="yapılandırılmamış"):
        rn.collect(tmp_path / "a" / "manifest.json", lambda *a: None, lambda: False, config=None)
    with pytest.raises(SourceError, match="konaklama çekimi"):
        rn.collect(tmp_path / "a" / "manifest.json", lambda *a: None, lambda: False, config={"settings": SETTINGS, "input": None})
    inputs = {"lodging_run_id": "L", "poi_run_id": "P", "beach_run_id": "B",
              "listings": [{"lodging_id": 1, "latitude": 30.3001, "longitude": -86.0990}, {"lodging_id": 2, "latitude": 12.0, "longitude": 12.0}],
              "points": [{"point_id": "node/9", "category_key": "pharmacy", "name": "Eczane", "brand": None, "latitude": 30.3199, "longitude": -86.0899}],
              "beaches": [{"external_id": "b1", "name": "Plaj", "latitude": 30.2999, "longitude": -86.0601}]}
    seen = []
    def handler(request):
        seen.append(request)
        if len(seen) <= 2:                                      # the Reader repeats a 5xx answer once; then the collector waits
            return httpx.Response(502, text="at capacity")
        return httpx.Response(200, content=json.dumps(ANSWER).encode(), headers={"content-type": "application/json"})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = rn.collect(tmp_path / "raw" / "manifest.json", lambda *a: None, lambda: False, config={"settings": SETTINGS, "input": inputs},
                            client=client, today=date(2026, 11, 16), waits=(0, 0))
    assert len(seen) == 3 and seen[0].url.params["data"] == rn.overpass_query(SETTINGS["area"], SETTINGS["speeds_mph"])
    assert "parking_aisle" not in seen[0].url.params["data"] and "motorway_link" in seen[0].url.params["data"]
    assert {r["category_key"] for r in result.records} == {"pharmacy", "beach", "extra:AIR"} and {r["lodging_id"] for r in result.records} == {1}
    assert all(r["road_km"] >= r["crow_km"] for r in result.records) and result.excluded_count == 1
    snapshot = result.related["snapshot"]
    assert (snapshot["lodging_run_id"], snapshot["poi_run_id"], snapshot["beach_run_id"], snapshot["measured_count"]) == ("L", "P", "B", 1)
    check = snapshot["checks"][0]
    assert check["osm_miles"] == pytest.approx(distance_km(30.30, -86.10, 30.30, -86.04) / rn.MILE_KM, abs=0.001) and check["difference_percent"] is not None
    manifest = json.loads((tmp_path / "raw" / "manifest.json").read_text(encoding="utf-8"))
    assert [r["status"] for r in manifest["responses"]] == [502, 502, 200] and len(manifest["responses"][-1]["raw_sha256"]) == 64
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(502, text="at capacity"))) as client:
        with pytest.raises(SourceError):
            rn.collect(tmp_path / "busy" / "manifest.json", lambda *a: None, lambda: False, config={"settings": SETTINGS, "input": inputs},
                       client=client, waits=(0,))


def test_api_stores_the_run_and_gives_road_and_great_circle_medians_side_by_side(tmp_path, monkeypatch):
    data = inventory()
    data[62708] = [lodging(3001, "Dune Allen condo", 62708, latitude="30.3001", longitude="-86.0700"),
                   lodging(3002, "Far away", 62708, latitude="35.0", longitude="-101.0")]
    stores = {"osm3s": {"timestamp_osm_base": "2026-10-09T11:34:06Z"}, "elements": [
        element("node", 21, 30.3100, -86.0690, shop="supermarket", name="Publix", brand="Publix"),
        element("node", 22, 30.3001, -86.0560, shop="supermarket", name="Publix", brand="Publix")]}
    real_points = dn.collect
    monkeypatch.setattr(dn, "collect", lambda path, progress, canceled, *, config, **kwargs: _points(real_points, stores, path, progress, canceled, config))
    def collect_roads(path, progress, canceled, *, config, **kwargs):
        handler = lambda request: httpx.Response(200, content=json.dumps(ANSWER).encode(), headers={"content-type": "application/json"})
        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            return REAL_COLLECT(path, progress, canceled, config={**config, "settings": {**config["settings"], "snap_limit_m": 1200}}, client=client,
                                today=date(2026, 11, 16))
    monkeypatch.setattr(rn, "collect", collect_roads)
    with TestClient(create_app(tmp_path / "data"), headers=HEADERS) as client:
        use(monkeypatch, BookDirectMock(data), date(2026, 10, 7))
        assert start(client)["status"] == "done"
        assert start(client, url=dn.SOURCE_URL)["status"] == "done"
        job = start(client, url=rn.SOURCE_URL)
        assert job["status"] == "done", job["message"]
        assert client.get("/api/bootstrap").json()["road_runs"][0]["id"] == job["id"]
        summary = client.get(f"/api/road-runs/{job['id']}").json()
        assert "trafik hesaba katılmadan" in summary["time_label"] and summary["attribution"] == "© OpenStreetMap katkıcıları, ODbL"
        assert summary["speeds_mph"] == thirty_a.ROAD_NETWORK["speeds_mph"] and summary["stale_inputs"] == []
        assert summary["unmeasured_count"] == summary["snapshot"]["listing_count"] - summary["snapshot"]["measured_count"] >= 1
        dune = next(r for r in summary["regions"] if r["region_id"] == "dune-allen")
        market = dune["measures"]["big_supermarket"]
        assert (dune["listing_count"], dune["measured_count"], market["count"]) == (2, 1, 1)
        assert market["road_median_km"] >= market["crow_median_km"] and market["changed_share"] == 1.0       # the road-nearest store is the other one
        assert market["most_common"]["target_key"] == "node/22" and market["minutes_median"] > 0
        assert {k for k in dune["measures"] if k.startswith("extra:")} == {"extra:VPS", "extra:ECP"}        # too far from the test network: no rows
        assert dune["measures"]["extra:VPS"]["count"] == 0
        raw = client.get(f"/api/road-runs/{job['id']}/raw")
        assert raw.status_code == 200 and json.loads(raw.content)["connector"] == rn.CONNECTOR_VERSION
        assert client.get("/api/road-runs/missing").status_code == 404
        with client.app.state.db.connect() as con:
            assert con.execute("PRAGMA foreign_key_check").fetchall() == []
            row = con.execute("SELECT * FROM road_nearest WHERE run_id=? AND category_key='big_supermarket' AND lodging_id=3001", (job["id"],)).fetchone()
            assert row["road_km"] >= row["crow_km"] and row["target_key"] != row["crow_nearest_key"]
            with pytest.raises(sqlite3.IntegrityError):                                # the table itself refuses a road shorter than the straight line
                con.execute("UPDATE road_nearest SET road_km=crow_km/2 WHERE run_id=? AND crow_km>0", (job["id"],))
        # a newer lodging run makes the stored road distances stale: the summary says so and the collector is due again
        assert start(client)["status"] == "done"
        assert client.get(f"/api/road-runs/{job['id']}").json()["stale_inputs"] == ["konaklama çekimi"]
        item = next(i for i in client.get("/api/refresh").json()["items"] if i["connector"] == rn.RoadNetworkConnector.name)
        assert item["due"] and "girdisi yenilendi" in item["due_reason"]


def _points(real, stores, path, progress, canceled, config):
    with httpx.Client(transport=httpx.MockTransport(points_mock(stores))) as client:
        return real(path, progress, canceled, config={**config, "reviewed_files": []}, client=client, today=date(2026, 10, 9))


def test_fresh_database_has_the_v20_configuration_and_v19_upgrades_keep_every_old_row(tmp_path):
    path = tmp_path / "data" / "studio.sqlite3"
    db = Database(path)
    db.initialize()
    context = db.context("30a")
    assert context.road_network["settings"] == json.loads(json.dumps(thirty_a.ROAD_NETWORK)) and "input" not in context.road_network
    assert context.airfare == {"airports": thirty_a.AIRFARE["airports"], "quarters": 5}
    with sqlite3.connect(path) as con:
        con.execute("INSERT INTO metadata VALUES ('gorev20','eski satır')")
        before = {name: con.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
                  for (name,) in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
        drop_v20(con, rows=True)
        con.execute("PRAGMA user_version=19")
    Database(path).initialize()
    with sqlite3.connect(path) as con:
        assert con.execute("PRAGMA user_version").fetchone()[0] == 21 and con.execute("PRAGMA foreign_key_check").fetchall() == []
        after = {name: con.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
                 for (name,) in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
        assert after == before and {name: after[name] for name in V20_TABLES} == V20_TABLES
        assert con.execute("SELECT value FROM metadata WHERE key='gorev20'").fetchone()[0] == "eski satır"
        assert [r[0] for r in con.execute("SELECT connector_name FROM destination_refresh_intervals ORDER BY sort_order")][-2:] == list(V20_INTERVALS)
        assert con.execute("SELECT COUNT(*) FROM sources WHERE url IN (?,?)", (rn.SOURCE_URL, "https://www.transtats.bts.gov/AverageFare/")).fetchone()[0] == 2
    assert len(list((path.parent / "backups").glob("studio-v19-*.sqlite3"))) == 1
    Database(path).initialize()                                 # a second opening adds nothing
    with sqlite3.connect(path) as con:
        assert con.execute("SELECT COUNT(*) FROM sources").fetchone()[0] == before["sources"]


def test_default_speeds_and_access_rules_are_settings_not_code():
    slow = {**SETTINGS, "speeds_mph": {**SETTINGS["speeds_mph"], "tertiary": 5}}
    answer = json.loads(json.dumps(ANSWER))
    for item in answer["elements"]:
        if item["type"] == "way":
            item["tags"].pop("maxspeed", None)
    fast_graph, _ = graph(answer=answer)
    slow_graph, _ = graph(slow, answer)
    a, b = (30.30, -86.10), (30.30, -86.09)
    assert trip(slow_graph, a, b, slow)[1] == pytest.approx(trip(fast_graph, a, b)[1] * SETTINGS["speeds_mph"]["tertiary"] / 5, rel=1e-6)
    open_all = {**SETTINGS, "closed_access": [], "restricted_access": []}
    g, _ = graph(open_all)
    assert g.way_count == 5                                      # the road tagged access=no is now a road like any other
