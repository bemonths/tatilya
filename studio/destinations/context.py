from dataclasses import dataclass


@dataclass(frozen=True)
class ConnectorContext:
    """Per-job SQLite snapshot, never shared mutable destination selection."""

    destination: dict
    canonical_regions: tuple[dict, ...]
    weather_anchors: tuple[dict, ...]
    climate_stations: tuple[dict, ...] = ()
    storm_corridor: dict | None = None
    lodging: dict | None = None
    agency: dict | None = None
    restaurants: dict | None = None
    browser_hosts: tuple[str, ...] = ()        # hosts read only with the computer's browser (they once showed a verification page)

