"""Case management models for internal CRM"""
from sqlalchemy import Column, String, Text, ForeignKey, Date, Enum as SQLEnum, Integer

from sqlalchemy.orm import relationship
import uuid
import enum

from app.models.base import Base, TimestampMixin


class CaseType(str, enum.Enum):
    """Type of case"""
    DEEMED_CONVEYANCE = "deemed_conveyance"
    RERA_REGISTRATION = "rera_registration"
    SELF_REDEVELOPMENT = "self_redevelopment"
    LEGAL_ADVISORY = "legal_advisory"
    FINANCIAL_ADVISORY = "financial_advisory"
    OTHER = "other"


class CaseStatus(str, enum.Enum):
    """Case status"""
    NEW = "new"
    IN_PROGRESS = "in_progress"
    PENDING_DOCUMENTS = "pending_documents"
    UNDER_REVIEW = "under_review"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"
    CANCELLED = "cancelled"


class CasePriority(str, enum.Enum):
    """Case priority"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Case(Base, TimestampMixin):
    """Case tracking (1,000+ deemed conveyance cases)"""
    __tablename__ = "cases"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    case_number = Column(String(50), unique=True, nullable=False, index=True)
    
    # Case details
    case_type = Column(SQLEnum(CaseType), nullable=False)
    status = Column(SQLEnum(CaseStatus), nullable=False, default=CaseStatus.NEW)
    priority = Column(SQLEnum(CasePriority), nullable=False, default=CasePriority.MEDIUM)
    
    # Client (can be member or society)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=True)
    society_id = Column(Integer, ForeignKey("societies.id"), nullable=True)
    
    # Assignment
    assigned_to_staff_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)
    
    # Timeline
    start_date = Column(Date, nullable=False)
    target_completion_date = Column(Date, nullable=True)
    actual_completion_date = Column(Date, nullable=True)
    
    # Details
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Created by
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Relationships
    member = relationship("Member", back_populates="cases")
    society = relationship("Society", back_populates="cases")
    assigned_to_staff = relationship("User", foreign_keys=[assigned_to_staff_id], backref="assigned_cases")
    branch = relationship("Branch", back_populates="cases")
    created_by = relationship("User", foreign_keys=[created_by_id], backref="created_cases")
    timeline_events = relationship("CaseTimeline", back_populates="case", cascade="all, delete-orphan")
    documents = relationship("CaseDocument", back_populates="case", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Case {self.case_number} - {self.case_type} - {self.status}>"


class CaseTimeline(Base, TimestampMixin):
    """Case timeline events"""
    __tablename__ = "case_timeline"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    
    event_type = Column(String(100), nullable=False)  # status_change, document_upload, note_added, etc.
    description = Column(Text, nullable=False)
    created_by_staff_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Relationships
    case = relationship("Case", back_populates="timeline_events")
    created_by = relationship("User", backref="case_timeline_entries")
    
    def __repr__(self):
        return f"<CaseTimeline {self.case_id} - {self.event_type}>"


class CaseDocument(Base, TimestampMixin):
    """Documents attached to cases"""
    __tablename__ = "case_documents"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    
    document_type = Column(String(100), nullable=False)  # application, agreement, proof, etc.
    file_name = Column(String(255), nullable=False)
    file_url = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=True)  # in bytes
    mime_type = Column(String(100), nullable=True)
    
    uploaded_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    notes = Column(Text, nullable=True)
    
    # Relationships
    case = relationship("Case", back_populates="documents")
    uploaded_by = relationship("User", backref="uploaded_case_documents")
    
    def __repr__(self):
        return f"<CaseDocument {self.file_name}>"

