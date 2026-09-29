from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Protocol


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
    raw_sha256: str
    metadata: dict = field(default_factory=dict)


class Connector(Protocol):
    name: str
    version: str
    raw_filename: str

    def supports(self, source: dict) -> bool: ...
    def collect(self, source: dict, raw_path: Path, progress: Callable, canceled: Callable) -> CollectionResult: ...
    def store_records(self, connection, run_id: str, records: list[dict]) -> None: ...
    def read_records(self, connection, run_id: str) -> list[dict]: ...
    def comparison_value(self, record: dict) -> dict: ...
