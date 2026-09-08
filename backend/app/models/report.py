import enum
import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import ARRAY, Column, Date, DateTime, Enum, ForeignKey, String, Text, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.db.session import Base

# CLIP ViT-B/32 image embeddings and all-MiniLM-L6-v2 text embeddings are
# both 512 / 384-dim respectively in practice; kept generic + configurable
# here. Adjust to match the actual model chosen in ml/ (Architecture Sec. 2).
IMAGE_EMBEDDING_DIM = 512
TEXT_EMBEDDING_DIM = 384


class ReportType(str, enum.Enum):
    LOST = "LOST"
    FOUND = "FOUND"


class ReportStatus(str, enum.Enum):
    # Lost lifecycle (SRS FR-14)
    SEARCHING = "SEARCHING"
    MATCH_FOUND = "MATCH_FOUND"
    RECOVERED = "RECOVERED"
    # Found lifecycle
    UNCLAIMED = "UNCLAIMED"
    POTENTIAL_OWNER_FOUND = "POTENTIAL_OWNER_FOUND"
    RETURNED = "RETURNED"
    # Shared terminal state
    CLOSED = "CLOSED"


# Valid status transitions per report type (SRS FR-14.1) — enforced in
# services/reports.py, never bypassed by direct field writes.
LOST_TRANSITIONS = {
    ReportStatus.SEARCHING: {ReportStatus.MATCH_FOUND, ReportStatus.CLOSED},
    ReportStatus.MATCH_FOUND: {ReportStatus.RECOVERED, ReportStatus.CLOSED},
    ReportStatus.RECOVERED: set(),
    ReportStatus.CLOSED: set(),
}
FOUND_TRANSITIONS = {
    ReportStatus.UNCLAIMED: {ReportStatus.POTENTIAL_OWNER_FOUND, ReportStatus.CLOSED},
    ReportStatus.POTENTIAL_OWNER_FOUND: {ReportStatus.RETURNED, ReportStatus.CLOSED},
    ReportStatus.RETURNED: set(),
    ReportStatus.CLOSED: set(),
}


class Report(Base):
    __tablename__ = "reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    type = Column(Enum(ReportType), nullable=False)
    title = Column(String, nullable=False)
    category = Column(String, nullable=False, index=True)
    color = Column(String, nullable=False)
    brand = Column(String, nullable=True)
    description = Column(Text, nullable=False)
    features = Column(Text, nullable=True)
    location = Column(String, nullable=False)
    report_date = Column(Date, nullable=False)
    report_time = Column(Time, nullable=True)

    status = Column(String, nullable=False)  # validated against the enums above
    image_urls = Column(ARRAY(String), nullable=False, default=list)

    image_embedding = Column(Vector(IMAGE_EMBEDDING_DIM), nullable=True)
    text_embedding = Column(Vector(TEXT_EMBEDDING_DIM), nullable=True)

    is_active = Column(String, nullable=False, default="true")  # simple soft-delete flag

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
