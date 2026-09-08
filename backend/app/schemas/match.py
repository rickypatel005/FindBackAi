import datetime
import json
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    lost_report_id: uuid.UUID
    found_report_id: uuid.UUID
    image_score: float
    text_score: float
    category_score: float
    color_score: float
    brand_score: float
    location_score: float
    time_score: float
    other_score: float
    final_score: float
    explanation: list[str] = Field(default_factory=list)
    created_at: datetime.datetime
    updated_at: datetime.datetime | None = None

    @field_validator("explanation", mode="before")
    @classmethod
    def _parse_explanation(cls, v):
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
                return [v]
            except Exception:
                return [v] if v else []
        return v or []
