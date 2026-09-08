import datetime
import uuid

from pydantic import BaseModel, ConfigDict


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    match_id: uuid.UUID
    title: str
    message: str
    is_read: bool
    created_at: datetime.datetime
