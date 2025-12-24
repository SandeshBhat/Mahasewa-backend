"""Invoice models"""
from sqlalchemy import Column, String, Integer, Numeric, ForeignKey, Date, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
import enum

from app.models.base import Base, TimestampMixin


class InvoiceType(str, enum.Enum):
    """Invoice type"""
    MEMBERSHIP = "membership"
    SUBSCRIPTION = "subscription"
    SERVICE_BOOKING = "service_booking"
    PUBLICATION = "publication"
    EVENT = "event"
    TRAINING = "training"
    OTHER = "other"


class InvoiceStatus(str, enum.Enum):
    """Invoice status"""
    DRAFT = "draft"
    PENDING = "pending"
    PAID = "paid"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class Invoice(Base, TimestampMixin):
    """Invoice for all transactions"""
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Invoice details
    invoice_number = Column(String(50), unique=True, nullable=False, index=True)
    invoice_type = Column(SQLEnum(InvoiceType), nullable=False)
    invoice_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=True)
    
    # Customer
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    customer_name = Column(String(255), nullable=False)
    customer_email = Column(String(255), nullable=False)
    customer_phone = Column(String(20), nullable=True)
    customer_address = Column(String(500), nullable=True)
    
    # Billing details
    billing_name = Column(String(255), nullable=True)
    billing_address = Column(String(500), nullable=True)
    billing_gstin = Column(String(20), nullable=True)
    
    # Amounts
    base_amount = Column(Numeric(10, 2), nullable=False)
    gst_rate = Column(Numeric(5, 2), default=18.00)  # 18%
    gst_amount = Column(Numeric(10, 2), nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)
    
    # Line items (JSON array)
    line_items = Column(JSON, nullable=False)  # [{description, quantity, rate, amount}]
    
    # Payment
    status = Column(SQLEnum(InvoiceStatus), default=InvoiceStatus.PENDING)
    payment_method = Column(String(50), nullable=True)
    payment_reference = Column(String(100), nullable=True)
    payment_date = Column(Date, nullable=True)
    
    # Documents
    pdf_url = Column(String(500), nullable=True)
    
    # Related records
    related_type = Column(String(50), nullable=True)  # society, member, service_provider, etc.
    related_id = Column(Integer, nullable=True)
    
    # Notes
    notes = Column(String(1000), nullable=True)
    
    # Relationships
    user = relationship("User", backref="invoices")
    
    def __repr__(self):
        return f"<Invoice {self.invoice_number} - ₹{self.total_amount}>"
