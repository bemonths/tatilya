from dataclasses import dataclass


@dataclass(frozen=True)
class ConnectorContext:
    """Per-job SQLite snapshot, never shared mutable destination selection."""

    destination: dict
    canonical_regions: tuple[dict, ...]
    weather_anchors: tuple[dict, ...]
    climate_stations: tuple[dict, ...] = ()
    storm_corridor: dict | None = None

