import datetime
import uuid

from pydantic import BaseModel, Field, model_validator

from app.models.report import ReportType


class ReportCreate(BaseModel):
    """
    Matches SRS FR-02.1: title, category, color, description, location,
    date, time, 1-3 images are required; brand is optional. `type` is fixed
    at creation and immutable afterward (FR-02.2).
    """

    title: str
    category: str
    color: str
    brand: str | None = None
    description: str
    features: str | None = None
    location: str
    report_date: datetime.date
    report_time: datetime.time | None = None
    image_urls: list[str] = Field(min_length=1, max_length=3)
    # Phase 3 — one CLIP embedding per entry in image_urls (same order),
    # collected client-side via POST /ai/embed-image on each uploaded
    # photo. Optional so older/simpler clients can still create reports
    # without images being embedded yet; averaged into a single vector on
    # the stored report per FR-06.2 (see services/reports.py).
    image_embeddings: list[list[float]] | None = None

    @model_validator(mode="after")
    def _embeddings_match_images(self) -> "ReportCreate":
        if self.image_embeddings is not None and len(self.image_embeddings) != len(self.image_urls):
            raise ValueError("image_embeddings, when provided, must have one entry per image_urls entry.")
        return self


class ReportUpdate(BaseModel):
    title: str | None = None
    category: str | None = None
    color: str | None = None
    brand: str | None = None
    description: str | None = None
    features: str | None = None
    location: str | None = None
    status: str | None = None


from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
import json

class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    type: ReportType
    title: str
    category: str
    color: str
    brand: str | None
    description: str
    features: str | None
    location: str
    report_date: datetime.date
    report_time: datetime.time | None
    status: str
    image_urls: list[str] = Field(default_factory=list)
    created_at: datetime.datetime

    @field_validator("image_urls", mode="before")
    @classmethod
    def _parse_image_urls(cls, v):
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
                return [v]
            except Exception:
                return [v] if v else []
        return v or []
