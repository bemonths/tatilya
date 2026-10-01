from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Protocol
from ..destinations.context import ConnectorContext


class SourceError(Exception):
    """Kullanıcıya gösterilmeye uygun, connector tarafından üretilen hata."""


class CollectionCanceled(Exception):
    pass


@dataclass
class CollectionResult:
    records: list[dict]
    total_count: int
    excluded_count: int
    source_updated: str | None
    metadata: dict = field(default_factory=dict)
    related: dict = field(default_factory=dict)


class Connector(Protocol):
    name: str
    version: str
    raw_filename: str
    method: str
    diff_enabled: bool

    def supports(self, source: dict) -> bool: ...
    def collect(self, source: dict, raw_path: Path, progress: Callable, canceled: Callable, *, context: ConnectorContext) -> CollectionResult: ...
    def store_records(self, connection, run_id: str, records: list[dict], related: dict | None = None) -> None: ...
    def read_records(self, connection, run_id: str) -> list[dict]: ...
    def comparison_value(self, record: dict) -> dict: ...
