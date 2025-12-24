"""Compliance tracking models"""
from sqlalchemy import Integer, JSON
from sqlalchemy import Column, String, Text, Boolean, ForeignKey, Date, Enum as SQLEnum

from sqlalchemy.orm import relationship
import uuid
import enum

from app.models.base import Base, TimestampMixin


class ComplianceCategory(str, enum.Enum):
    """Compliance category"""
    ANNUAL_FILING = "annual_filing"
    AUDIT = "audit"
    REGISTRATION = "registration"
    LICENSING = "licensing"
    TAX = "tax"
    STATUTORY = "statutory"
    OTHER = "other"


class ComplianceFrequency(str, enum.Enum):
    """Frequency of compliance"""
    ONE_TIME = "one_time"
    ANNUAL = "annual"
    QUARTERLY = "quarterly"
    MONTHLY = "monthly"
    AS_NEEDED = "as_needed"


class SubmissionStatus(str, enum.Enum):
    """Submission status"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    OVERDUE = "overdue"


class ComplianceRequirement(Base, TimestampMixin):
    """Compliance requirements for societies"""
    __tablename__ = "compliance_requirements"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(SQLEnum(ComplianceCategory), nullable=False)
    frequency = Column(SQLEnum(ComplianceFrequency), nullable=False)
    
    # Applicability
    is_mandatory = Column(Boolean, default=True)
    applicable_to = Column(JSON, nullable=True)  # Array: ["all", "specific_states", etc.]
    
    # Requirements
    required_documents = Column(JSON, nullable=True)  # Array of required documents
    checklist = Column(JSON, nullable=True)  # Array of checklist items
    
    # Reference
    legal_reference = Column(Text, nullable=True)
    reference_url = Column(String(500), nullable=True)
    
    is_active = Column(Boolean, default=True)
    
    # Relationships
    submissions = relationship("ComplianceSubmission", back_populates="requirement")
    
    def __repr__(self):
        return f"<ComplianceRequirement {self.name}>"


class ComplianceSubmission(Base, TimestampMixin):
    """Compliance submissions by societies"""
    __tablename__ = "compliance_submissions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    society_id = Column(Integer, ForeignKey("societies.id"), nullable=False)
    requirement_id = Column(Integer, ForeignKey("compliance_requirements.id"), nullable=False)
    
    # Period
    applicable_period = Column(String(100), nullable=True)  # "FY 2023-24", "Q1 2024", etc.
    
    # Deadlines
    due_date = Column(Date, nullable=False)
    submission_date = Column(Date, nullable=True)
    
    # Status
    status = Column(SQLEnum(SubmissionStatus), nullable=False, default=SubmissionStatus.NOT_STARTED)
    
    # Documents
    submitted_documents = Column(JSON, nullable=True)  # Array of document URLs
    
    # Verification
    verified_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    verification_date = Column(Date, nullable=True)
    verification_notes = Column(Text, nullable=True)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Relationships
    society = relationship("Society", backref="compliance_submissions")
    requirement = relationship("ComplianceRequirement", back_populates="submissions")
    verified_by = relationship("User", backref="verified_compliance_submissions")
    
    def __repr__(self):
        return f"<ComplianceSubmission {self.society_id} - {self.requirement_id}>"

