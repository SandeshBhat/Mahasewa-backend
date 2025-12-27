"""Consultation booking models"""
from sqlalchemy import Column, String, Text, Numeric, ForeignKey, DateTime, Enum as SQLEnum, Integer

from sqlalchemy.orm import relationship
import uuid
import enum

from app.models.base import Base, TimestampMixin


class ConsultationStatus(str, enum.Enum):
    """Consultation status"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class ConsultationType(str, enum.Enum):
    """Consultation type"""
    ONLINE = "online"
    IN_PERSON = "in_person"


class Consultation(Base, TimestampMixin):
    """Consultation bookings"""
    __tablename__ = "consultations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Client
    client_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Branch tracking
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)
    
    # Provider
    provider_id = Column(Integer, ForeignKey("service_providers.id"), nullable=False)
    
    # Consultation details
    consultation_type = Column(SQLEnum(ConsultationType), nullable=False)
    status = Column(SQLEnum(ConsultationStatus), nullable=False, default=ConsultationStatus.PENDING)
    
    # Schedule
    scheduled_datetime = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, default=60)
    
    # For online consultations
    meeting_url = Column(String(500), nullable=True)
    meeting_id = Column(String(255), nullable=True)
    meeting_password = Column(String(255), nullable=True)
    
    # For in-person consultations
    venue = Column(String(255), nullable=True)
    venue_address = Column(Text, nullable=True)
    
    # Topic/Purpose
    subject = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Payment
    fee = Column(Numeric(10, 2), nullable=False)
    payment_status = Column(String(50), default="pending")
    payment_id = Column(String(100), nullable=True)
    
    # Notes
    client_notes = Column(Text, nullable=True)
    provider_notes = Column(Text, nullable=True)
    
    # Feedback
    client_rating = Column(Integer, nullable=True)  # 1-5
    client_feedback = Column(Text, nullable=True)
    
    # Relationships
    client = relationship("User", foreign_keys=[client_user_id], backref="consultations_as_client")
    branch = relationship("Branch", backref="consultations")
    provider = relationship("ServiceProvider", backref="consultations")
    
    def __repr__(self):
        return f"<Consultation {self.id} - {self.status}>"

