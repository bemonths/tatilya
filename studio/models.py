from typing import Literal
from urllib.parse import urlsplit, urlunsplit

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from .catalog import CADENCES, CATEGORIES, METHODS


class SourceInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    destination_id: str = Field(min_length=1, max_length=80)
    scope_region_id: str | None = None
    name: str = Field(min_length=2, max_length=160)
    url: HttpUrl
    category: str = "Genel"
    region: str = Field(default="", max_length=160)
    method: str = "Belirlenecek"
    cadence: str = "Haftalık"
    notes: str = Field(default="", max_length=3000)
    enabled: bool = True

    @field_validator("category", "method", "cadence")
    @classmethod
    def known_value(cls, value, info):
        choices = {"category": CATEGORIES, "method": METHODS, "cadence": CADENCES}
        if value not in choices[info.field_name]:
            raise ValueError("Listeden geçerli bir değer seçin.")
        return value

    @field_validator("url")
    @classmethod
    def no_credentials(cls, value):
        if value.username is not None or value.password is not None:
            raise ValueError("Kaynak adresine kullanıcı adı veya parola eklemeyin.")
        return value

    def record(self):
        data = self.model_dump(mode="json")
        parts = urlsplit(data["url"])
        data["url"] = urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, ""))
        return data


class SourceUpdate(SourceInput):
    destination_id: str | None = None
    expected_version: int = Field(ge=1)


class JobInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["catalog_audit", "source_collection", "beach_collection"] = "catalog_audit"
    destination_id: str | None = None
    source_id: str | None = Field(default=None, min_length=1, max_length=64)


class EvidencePackInput(BaseModel):
    """An evidence pack request: a template of the destination and its parameter values (a region id per region parameter)."""
    model_config = ConfigDict(extra="forbid")
    destination_id: str | None = None
    template_key: str = Field(min_length=1, max_length=64)
    params: dict[str, str] = Field(default_factory=dict)
