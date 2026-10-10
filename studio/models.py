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


class TitleRunInput(BaseModel):
    """A topic and title proposal request (GÖREV-13): region (required; the whole destination or a neighborhood), content family or all, note."""
    model_config = ConfigDict(extra="forbid")
    destination_id: str | None = None
    bolge: str = Field(min_length=1, max_length=100)
    aile: str | None = Field(default=None, max_length=100)
    not_: str | None = Field(default=None, alias="not", max_length=4000)


class RunDecisionInput(BaseModel):
    """A decision on a Claude run: the candidate to choose (for "Seç"), the user's note and (GÖREV-14) the title as the user edited it."""
    model_config = ConfigDict(extra="forbid")
    aday: int | None = Field(default=None, ge=0, le=100)
    not_: str | None = Field(default=None, alias="not", max_length=4000)
    baslik_en: str | None = Field(default=None, max_length=200)
    baslik_tr: str | None = Field(default=None, max_length=300)


class ReviewRunInput(BaseModel):
    """GÖREV-14: the user's own title or idea to evaluate, with a region and an optional note."""
    model_config = ConfigDict(extra="forbid")
    destination_id: str | None = None
    bolge: str = Field(min_length=1, max_length=100)
    baslik: str = Field(min_length=1, max_length=500)
    not_: str | None = Field(default=None, alias="not", max_length=4000)


class TranslateInput(BaseModel):
    """GÖREV-14: a candidate whose Turkish title the user changed; Claude writes the English title."""
    model_config = ConfigDict(extra="forbid")
    aday: int = Field(ge=0, le=100)
    baslik_tr: str = Field(min_length=1, max_length=300)


class TextRunInput(BaseModel):
    """GÖREV-15: "Metni yaz" — the tones (file stems) a new text run writes, each with the same plan."""
    model_config = ConfigDict(extra="forbid")
    tonlar: list[str] = Field(min_length=1, max_length=12)


class TextToneInput(BaseModel):
    """GÖREV-15: "Bu tonla da yaz" — one more tone with a run's plan."""
    model_config = ConfigDict(extra="forbid")
    ton: str = Field(min_length=1, max_length=80)


class TextSelectInput(BaseModel):
    """GÖREV-15: "Bu tonla devam et"."""
    model_config = ConfigDict(extra="forbid")
    not_: str | None = Field(default=None, alias="not", max_length=2000)


class ToneInput(BaseModel):
    """GÖREV-15: Settings → Tonlar: a new tone, or a tone's new name and text (with the SHA-256 of the file as it was opened)."""
    model_config = ConfigDict(extra="forbid")
    ad: str = Field(max_length=200)
    metin: str = Field(max_length=20000)
    base_sha256: str | None = Field(default=None, max_length=64)


class ToneRestoreInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    base_sha256: str = Field(min_length=64, max_length=64)
