import uuid

from sqlalchemy import ARRAY, Column, DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.db.session import Base


class Match(Base):
    """
    Per SRS FR-08 / FR-10 and Architecture Data Model. Every component score
    is persisted so explanations (FR-10.2) are always traceable back to a
    stored value — never generated independently of the scoring engine.
    """

    __tablename__ = "matches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lost_report_id = Column(UUID(as_uuid=True), ForeignKey("reports.id"), nullable=False, index=True)
    found_report_id = Column(UUID(as_uuid=True), ForeignKey("reports.id"), nullable=False, index=True)

    image_score = Column(Float, nullable=False, default=0.0)
    text_score = Column(Float, nullable=False, default=0.0)
    category_score = Column(Float, nullable=False, default=0.0)
    color_score = Column(Float, nullable=False, default=0.0)
    brand_score = Column(Float, nullable=False, default=0.0)
    location_score = Column(Float, nullable=False, default=0.0)
    time_score = Column(Float, nullable=False, default=0.0)
    other_score = Column(Float, nullable=False, default=0.0)

    final_score = Column(Float, nullable=False, default=0.0, index=True)
    explanation = Column(ARRAY(String), nullable=False, default=list)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # Phase 6 (migrations/004_match_constraints.sql) — bumped whenever
    # find_and_persist_matches upserts an existing (lost, found) pair
    # instead of inserting a new row.
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
