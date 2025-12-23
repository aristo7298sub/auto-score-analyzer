from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.core.database import Base


class FileParseSession(Base):
    __tablename__ = "file_parse_sessions"

    id = Column(String(36), primary_key=True, index=True)  # uuid
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    score_file_id = Column(Integer, ForeignKey("score_files.id", ondelete="CASCADE"), index=True, nullable=False)

    status = Column(String(20), nullable=False, index=True)  # previewed/confirmed/expired

    file_type = Column(String(20), nullable=False)

    ir_json = Column(Text, nullable=False)
    ai_mapping_json = Column(Text, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
