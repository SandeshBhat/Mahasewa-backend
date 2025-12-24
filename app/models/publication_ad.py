"""
Publication Ad models
"""
from sqlalchemy import Column, String, Text, Boolean, Integer, ForeignKey, Numeric, Date
from sqlalchemy.orm import relationship
from datetime import date

from app.models.base import Base, TimestampMixin


class PublicationAd(Base, TimestampMixin):
    """Publication advertisement bookings"""
    __tablename__ = "publication_ads"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Vendor
    vendor_id = Column(Integer, ForeignKey("service_providers.id", ondelete="CASCADE"), nullable=False)
    
    # Publication details
    publication_issue = Column(String(100), nullable=False)  # e.g., "January 2025"
    page_color = Column(String(50), nullable=False)  # "bw", "color", "premium_color"
    page_size = Column(String(50), nullable=False)  # "full", "half", "quarter"
    position = Column(String(50), nullable=False)  # "front_cover", "back_cover", "inside"
    total_price = Column(Numeric(10, 2), nullable=False)
    
    # Ad content
    ad_content = Column(Text, nullable=True)
    contact_name = Column(String(255), nullable=False)
    contact_email = Column(String(255), nullable=False)
    contact_phone = Column(String(20), nullable=True)
    notes = Column(Text, nullable=True)
    
    # Status
    status = Column(String(50), default="pending")  # "pending", "approved", "rejected", "published"
    deadline = Column(Date, nullable=True)
    
    # Payment
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True)
    payment_status = Column(String(50), default="pending")
    
    # Relationships
    vendor = relationship("ServiceProvider", backref="publication_ads")
    # invoice = relationship("Invoice", backref="publication_ad", foreign_keys=[invoice_id])  # Uncomment when Invoice model exists
    
    def __repr__(self):
        return f"<PublicationAd {self.id} - {self.publication_issue}>"
