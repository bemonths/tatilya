"""Small spherical-earth helpers shared by destination-independent connectors (no external dependencies)."""
import math

EARTH_RADIUS_KM = 6371.0088  # IUGG mean radius
KM_PER_NMI = 1.852


def unit_vector(latitude, longitude):
    lat, lon = math.radians(latitude), math.radians(longitude)
    return (math.cos(lat) * math.cos(lon), math.cos(lat) * math.sin(lon), math.sin(lat))


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _norm(a):
    return math.sqrt(_dot(a, a))


def angle(a, b):
    """Great-circle angle between two unit vectors (radians), numerically stable."""
    return math.atan2(_norm(_cross(a, b)), _dot(a, b))


def distance_km(lat1, lon1, lat2, lon2):
    return EARTH_RADIUS_KM * angle(unit_vector(lat1, lon1), unit_vector(lat2, lon2))


class Segment:
    """Great-circle segment between two points (the shorter arc); distance from any point in km."""

    def __init__(self, west, east):
        self.a, self.b = unit_vector(*west), unit_vector(*east)
        normal = _cross(self.a, self.b)
        length = _norm(normal)
        if length == 0:
            raise ValueError("Segment endpoints must differ.")
        self.normal = tuple(value / length for value in normal)

    def distance_km(self, latitude, longitude):
        p = unit_vector(latitude, longitude)
        offset = _dot(p, self.normal)
        projected = tuple(p[i] - offset * self.normal[i] for i in range(3))
        # The projection lies on the arc when it is on the inner side of both endpoints.
        if _norm(projected) > 0 and _dot(_cross(self.a, projected), self.normal) >= 0 and _dot(_cross(projected, self.b), self.normal) >= 0:
            return EARTH_RADIUS_KM * abs(math.asin(max(-1.0, min(1.0, offset))))
        return EARTH_RADIUS_KM * min(angle(p, self.a), angle(p, self.b))
