"""Service booking models"""
from sqlalchemy import Column, String, Text, Numeric, Integer, ForeignKey, DateTime, Enum as SQLEnum, JSON

from sqlalchemy.orm import relationship
import uuid
import enum

from app.models.base import Base, TimestampMixin


class BookingStatus(str, enum.Enum):
    """Service booking status"""
    REQUESTED = "requested"
    QUOTE_PROVIDED = "quote_provided"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ServiceBooking(Base, TimestampMixin):
    """Service bookings"""
    __tablename__ = "service_bookings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    booking_number = Column(String(50), unique=True, nullable=False, index=True)
    
    # Client (can be society or individual)
    client_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    society_id = Column(Integer, ForeignKey("societies.id"), nullable=True)
    
    # Provider & Service
    provider_id = Column(Integer, ForeignKey("service_providers.id"), nullable=False)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=True)
    
    # Booking details
    status = Column(SQLEnum(BookingStatus), nullable=False, default=BookingStatus.REQUESTED)
    service_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    requirements = Column(JSON, nullable=True)  # Specific requirements
    
    # Timeline
    requested_start_date = Column(DateTime, nullable=True)
    actual_start_date = Column(DateTime, nullable=True)
    expected_completion_date = Column(DateTime, nullable=True)
    actual_completion_date = Column(DateTime, nullable=True)
    
    # Quote
    quote_amount = Column(Numeric(10, 2), nullable=True)
    final_amount = Column(Numeric(10, 2), nullable=True)
    quote_details = Column(JSON, nullable=True)  # Breakdown
    
    # Payment
    payment_status = Column(String(50), default="pending")
    payment_id = Column(String(100), nullable=True)
    advance_paid = Column(Numeric(10, 2), default=0)
    
    # Notes
    client_notes = Column(Text, nullable=True)
    provider_notes = Column(Text, nullable=True)
    
    # Feedback & Rating
    client_rating = Column(Integer, nullable=True)  # 1-5
    client_feedback = Column(Text, nullable=True)
    
    # Relationships
    client = relationship("User", foreign_keys=[client_user_id], backref="service_bookings")
    society = relationship("Society", backref="service_bookings")
    provider = relationship("ServiceProvider", backref="service_bookings")
    service = relationship("Service", backref="bookings")
    
    def __repr__(self):
        return f"<ServiceBooking {self.booking_number} - {self.status}>"

