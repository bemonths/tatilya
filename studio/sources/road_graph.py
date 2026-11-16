"""A drivable road graph from OpenStreetMap ways and the fastest routes on it (no external dependencies, no I/O).

Generic core. Which highway types are roads, their default speeds, which access values close a road or make it usable only at the
two ends of a trip, and how far a point may be from a road all come from the caller's settings (the destination configuration);
nothing about a destination is written here.

Lengths are great-circle lengths between consecutive OpenStreetMap nodes, and a point is tied to the network by the straight
(great-circle) leg to the nearest point of the nearest road segment. A route's length is therefore never shorter than the
great-circle distance between its two ends (triangle inequality). Driving time is length ÷ speed per segment: the way's own
`maxspeed` when it can be read, else the configured default of its highway type; no traffic, signals or turns are modelled.

Routes minimize driving time. Roads with a restricted access value (private, customers, destination, ...) may be used only in one
unbroken run at the start of a trip and one at its end, never to cut through.
"""
import heapq
import json
import math
import re

from .geo import distance_km

MPH_KMH = 1.609344
CELL = 0.004                    # degrees; grid cell of the segment index (about 400 m)
_SPEED = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*(mph|km/h|kmh|kph)?\s*$", re.I)
PHASES = 3                      # backward search: 0 = the trip's restricted end run, 1 = public middle, 2 = restricted start run
AT_NODE_KM = 1e-6               # a point snapped onto the end of a segment stands at that junction: any road of the junction serves it


class RoadDataError(ValueError):
    """The road answer is not the expected Overpass JSON."""


def parse(body):
    """(nodes {id: (lat, lon)}, ways [{id, nodes, tags}], other tagged elements, OpenStreetMap timestamp) of an Overpass answer."""
    try:
        data = json.loads(body)
        elements = data["elements"]
    except (ValueError, KeyError, TypeError) as exc:
        raise RoadDataError("Overpass yanıtı beklenen JSON biçiminde değil.") from exc
    if not isinstance(elements, list):
        raise RoadDataError("Overpass yanıtında öğe listesi yok.")
    nodes, ways, others = {}, [], []
    for element in elements:
        if not isinstance(element, dict):
            continue
        kind, tags = element.get("type"), element.get("tags") or {}
        if kind == "node" and isinstance(element.get("lat"), (int, float)) and isinstance(element.get("lon"), (int, float)):
            nodes[element["id"]] = (float(element["lat"]), float(element["lon"]))
        if kind == "way" and "highway" in tags and isinstance(element.get("nodes"), list):
            ways.append({"id": element["id"], "nodes": element["nodes"], "tags": tags})
        elif tags and "highway" not in tags:
            others.append(element)
    stamp = (data.get("osm3s") or {}).get("timestamp_osm_base") if isinstance(data, dict) else None
    return nodes, ways, others, stamp


def speed_mph(tags, defaults):
    """(mph, source) of a way: its `maxspeed` ("35 mph", or a bare number in km/h) or the default of its highway type."""
    raw = (tags.get("maxspeed") or "").split(";")[0]
    found = _SPEED.match(raw)
    if found and float(found.group(1)) > 0:
        value = float(found.group(1))
        return (value if (found.group(2) or "").lower() == "mph" else value / MPH_KMH), "maxspeed"
    return float(defaults[tags["highway"]]), "default"


def access_of(tags, settings):
    """'closed', 'restricted' or 'open' for motor cars: the most specific of motorcar, motor_vehicle, vehicle, access decides."""
    for key in ("motorcar", "motor_vehicle", "vehicle", "access"):
        value = tags.get(key)
        if value is None:
            continue
        if value in settings.get("closed_access", ()):
            return "closed"
        if value in settings.get("restricted_access", ()):
            return "restricted"
        return "open"
    return "open"


def directions(tags):
    """(forward, backward) allowed along the way's node order."""
    oneway = tags.get("oneway")
    if oneway in ("-1", "reverse"):
        return False, True
    if oneway in ("yes", "true", "1") or (oneway is None and (tags.get("junction") in ("roundabout", "circular")
                                                                or tags["highway"] in ("motorway", "motorway_link"))):
        return True, False
    return True, True


class Graph:
    """Directed road graph. Nodes are dense indices; `out[n]` and `back[n]` hold (other node, km, hours, restricted)."""

    def __init__(self):
        self.ids, self.index, self.points = [], {}, []
        self.out, self.back = [], []
        self.segments = []          # (a, b, km, hours, restricted, forward, backward, way id, snap allowed)
        self.grid = {}
        self.way_count = 0
        self.km = 0.0
        self.speed_sources = {"maxspeed": 0.0, "default": 0.0}     # km of road by where its speed came from
        self.refs = {}              # ref text -> km (each segment once)

    def node(self, osm_id, point):
        found = self.index.get(osm_id)
        if found is None:
            found = self.index[osm_id] = len(self.ids)
            self.ids.append(osm_id)
            self.points.append(point)
            self.out.append([])
            self.back.append([])
        return found

    def add_segment(self, a, b, hours_per_km, restricted, forward, backward, way_id, snap):
        km = distance_km(*self.points[a], *self.points[b])
        if km <= 0:
            return 0.0
        hours = km * hours_per_km
        if forward:
            self.out[a].append((b, km, hours, restricted))
            self.back[b].append((a, km, hours, restricted))
        if backward:
            self.out[b].append((a, km, hours, restricted))
            self.back[a].append((b, km, hours, restricted))
        number = len(self.segments)
        self.segments.append((a, b, km, hours, restricted, forward, backward, way_id, snap))
        if snap:
            (lat1, lon1), (lat2, lon2) = self.points[a], self.points[b]
            for row in range(int(math.floor(min(lat1, lat2) / CELL)), int(math.floor(max(lat1, lat2) / CELL)) + 1):
                for column in range(int(math.floor(min(lon1, lon2) / CELL)), int(math.floor(max(lon1, lon2) / CELL)) + 1):
                    self.grid.setdefault((row, column), []).append(number)
        return km

    # --- tying a point to the network --------------------------------------------------------------------------------------

    def snap(self, latitude, longitude, limit_km):
        """The nearest point of the nearest road segment within `limit_km`: {segment, point, leg_km, to_a_km, to_b_km}, or None."""
        row, column = int(math.floor(latitude / CELL)), int(math.floor(longitude / CELL))
        reach = max(1, int(math.ceil(limit_km / (CELL * 111.0 * math.cos(math.radians(latitude))))) + 1)
        scale = math.cos(math.radians(latitude))
        best = None
        for ring in range(reach + 1):
            for r in range(row - ring, row + ring + 1):
                for c in range(column - ring, column + ring + 1):
                    if max(abs(r - row), abs(c - column)) != ring:
                        continue
                    for number in self.grid.get((r, c), ()):
                        a, b = self.segments[number][0], self.segments[number][1]
                        (lat1, lon1), (lat2, lon2) = self.points[a], self.points[b]
                        dx, dy = (lon2 - lon1) * scale, lat2 - lat1
                        px, py = (longitude - lon1) * scale, latitude - lat1
                        span = dx * dx + dy * dy
                        t = 0.0 if span == 0 else max(0.0, min(1.0, (px * dx + py * dy) / span))
                        off = (px - t * dx) ** 2 + (py - t * dy) ** 2
                        if best is None or off < best[0]:
                            best = (off, number, t)
            # a segment in a farther ring cannot be nearer than the rings already searched once the best is inside them
            if best is not None and math.sqrt(best[0]) * 111.0 <= ring * CELL * 111.0 * min(1.0, scale):
                break
        if best is None:
            return None
        _, number, t = best
        a, b = self.segments[number][0], self.segments[number][1]
        (lat1, lon1), (lat2, lon2) = self.points[a], self.points[b]
        point = (lat1 + t * (lat2 - lat1), lon1 + t * (lon2 - lon1))
        leg = distance_km(latitude, longitude, *point)
        if leg > limit_km:
            return None
        return {"segment": number, "point": point, "leg_km": leg, "to_a_km": distance_km(*point, *self.points[a]),
                "to_b_km": distance_km(*point, *self.points[b])}

    # --- routes ------------------------------------------------------------------------------------------------------------

    def to_target(self, snap):
        """Fastest way from every node to a snapped target, searched backward from it: (hours, km) lists indexed node*3+phase,
        the phase telling which kinds of roads the way from that node on uses (see the module text)."""
        a, b, km, hours, restricted, forward, backward, _, _ = self.segments[snap["segment"]]
        per_km = hours / km
        size = len(self.ids) * PHASES
        best_hours, best_km = [math.inf] * size, [0.0] * size
        phase = 0 if restricted else 1
        heap = []
        for node, part, allowed in ((a, snap["to_a_km"], forward), (b, snap["to_b_km"], backward)):
            if allowed or part <= AT_NODE_KM:        # the trip arrives over the target's own segment, from that end (or at the junction)
                state = node * PHASES + phase
                if part * per_km < best_hours[state]:
                    best_hours[state], best_km[state] = part * per_km, part
                    heapq.heappush(heap, (part * per_km, state))
        back = self.back
        while heap:
            cost, state = heapq.heappop(heap)
            if cost > best_hours[state]:
                continue
            node, phase = divmod(state, PHASES)
            distance = best_km[state]
            for other, km, hours, restricted in back[node]:
                if restricted:
                    following = 0 if phase == 0 else 2
                elif phase == 2:
                    continue                 # a public road before a restricted run that is not the trip's start: cutting through
                else:
                    following = 1
                target = other * PHASES + following
                if cost + hours < best_hours[target]:
                    best_hours[target], best_km[target] = cost + hours, distance + km
                    heapq.heappush(heap, (cost + hours, target))
        return best_hours, best_km

    def trip(self, origin, target, table, snap_hours_per_km):
        """(km, hours) of the fastest trip from a snapped origin to the snapped target `table` was searched for, legs included;
        None when no road joins them."""
        best_hours, best_km = table
        a, b, km, hours, restricted, forward, backward, _, _ = self.segments[origin["segment"]]
        per_km = hours / km
        phases = (0, 1, 2) if restricted else (0, 1)      # after a public first segment a restricted run may only be the trip's end
        found = None
        for node, part, allowed in ((b, origin["to_b_km"], forward), (a, origin["to_a_km"], backward)):
            if not allowed and part > AT_NODE_KM:
                continue
            for phase in phases:
                state = node * PHASES + phase
                if best_hours[state] < math.inf:
                    candidate = (best_hours[state] + part * per_km, best_km[state] + part)
                    if found is None or candidate < found:
                        found = candidate
        if origin["segment"] == target["segment"]:        # both on one segment: along it, in an allowed direction
            ahead = origin["to_a_km"] <= target["to_a_km"]
            if (ahead and forward) or (not ahead and backward) or origin["to_a_km"] == target["to_a_km"]:
                along = distance_km(*origin["point"], *target["point"])
                candidate = (along * per_km, along)
                if found is None or candidate < found:
                    found = candidate
        if found is None:
            return None
        legs = origin["leg_km"] + target["leg_km"]
        return found[1] + legs, found[0] + legs * snap_hours_per_km


def build(nodes, ways, settings):
    """The road graph of the ways whose highway type the settings list, closed and skipped ways left out."""
    defaults = settings["speeds_mph"]
    skipped_service = set(settings.get("skipped_service", ()))
    no_snap = set(settings.get("no_snap", ()))
    graph = Graph()
    for way in ways:
        tags = way["tags"]
        if tags["highway"] not in defaults or tags.get("area") == "yes":
            continue
        if tags["highway"] == "service" and tags.get("service") in skipped_service:
            continue
        access = access_of(tags, settings)
        if access == "closed":
            continue
        mph, source = speed_mph(tags, defaults)
        hours_per_km = 1.0 / (mph * MPH_KMH)
        forward, backward = directions(tags)
        snap = tags["highway"] not in no_snap
        points = [n for n in way["nodes"] if n in nodes]
        added = 0.0
        for first, second in zip(points, points[1:]):
            a, b = graph.node(first, nodes[first]), graph.node(second, nodes[second])
            added += graph.add_segment(a, b, hours_per_km, access == "restricted", forward, backward, way["id"], snap)
        if added:
            graph.way_count += 1
            graph.km += added
            graph.speed_sources[source] += added
            for ref in (tags.get("ref") or "").split(";"):
                if ref.strip():
                    graph.refs[ref.strip()] = graph.refs.get(ref.strip(), 0.0) + added
    return graph
