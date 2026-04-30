import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Boolean,
    DateTime, Text, ForeignKey, Enum as SAEnum
)
from sqlalchemy.orm import relationship
from database import Base


def gen_uuid():
    return str(uuid.uuid4())


class Scan(Base):
    __tablename__ = "scans"

    id = Column(String, primary_key=True, default=gen_uuid)
    repo_full_name = Column(String, nullable=False)
    repo_url = Column(String, nullable=True)
    scanned_by = Column(String, nullable=False)
    scanned_at = Column(DateTime, default=datetime.utcnow)
    total_files = Column(Integer, default=0)
    health_score = Column(Float, nullable=True)
    progress = Column(Integer, default=0)       # 0-100
    status_message = Column(String, nullable=True)  # human-readable progress message
    status = Column(
        SAEnum("pending", "running", "complete", "failed", name="scan_status"),
        default="pending"
    )

    findings = relationship("Finding", back_populates="scan", cascade="all, delete-orphan")
    decisions = relationship("Decision", back_populates="scan", cascade="all, delete-orphan")


class Finding(Base):
    __tablename__ = "findings"

    id = Column(String, primary_key=True, default=gen_uuid)
    scan_id = Column(String, ForeignKey("scans.id"), nullable=False)
    severity = Column(
        SAEnum("critical", "warning", "suggestion", name="finding_severity"),
        nullable=False
    )
    category = Column(
        SAEnum("security", "bug", "quality", "performance", name="finding_category"),
        nullable=False
    )
    file_path = Column(String, nullable=False)
    line_start = Column(Integer, default=1)
    line_end = Column(Integer, default=1)
    title = Column(String, nullable=False)
    explanation = Column(Text, nullable=False)
    suggested_fix = Column(Text, nullable=True)
    confidence = Column(Float, default=0.8)
    source = Column(
        SAEnum("armorclaw", "gemini", name="finding_source"),
        nullable=False
    )
    status = Column(
        SAEnum("pending", "accepted", "edited", "dismissed", name="finding_status"),
        default="pending"
    )
    armorclaw_rule_id = Column(String, nullable=True)
    armoriq_intent_verified = Column(Boolean, default=False)
    armoriq_policy_blocked = Column(Boolean, default=False)

    scan = relationship("Scan", back_populates="findings")
    decisions = relationship("Decision", back_populates="finding", cascade="all, delete-orphan")


class Decision(Base):
    __tablename__ = "decisions"

    id = Column(String, primary_key=True, default=gen_uuid)
    finding_id = Column(String, ForeignKey("findings.id"), nullable=False)
    scan_id = Column(String, ForeignKey("scans.id"), nullable=False)
    action = Column(
        SAEnum("accepted", "edited", "dismissed", name="decision_action"),
        nullable=False
    )
    edited_fix = Column(Text, nullable=True)
    decided_by = Column(String, nullable=False)
    decided_at = Column(DateTime, default=datetime.utcnow)
    armoriq_audit_log_id = Column(String, nullable=True)
    github_issue_url = Column(String, nullable=True)

    finding = relationship("Finding", back_populates="decisions")
    scan = relationship("Scan", back_populates="decisions")
