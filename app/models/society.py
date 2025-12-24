"""Society models"""
from sqlalchemy import Column, String, Text, Boolean, Integer, ForeignKey, Date, JSON, Numeric

from sqlalchemy.orm import relationship
import uuid

from app.models.base import Base, TimestampMixin


class Society(Base, TimestampMixin):
    """Housing Societies"""
    __tablename__ = "societies"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    registration_number = Column(String(100), unique=True, nullable=True)
    
    # Address
    address = Column(String(500), nullable=False)
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)
    pincode = Column(String(10), nullable=True)
    
    # Location coordinates (for distance calculation)
    latitude = Column(Numeric(10, 7), nullable=True)
    longitude = Column(Numeric(10, 7), nullable=True)
    
    # Contact
    phone = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    
    # Details
    total_units = Column(Integer, nullable=True)
    total_members = Column(Integer, default=0)
    year_established = Column(Integer, nullable=True)
    registration_date = Column(Date, nullable=True)
    
    # Admin (Society Admin user)
    admin_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Documents
    documents = Column(JSON, nullable=True)  # Array of document URLs
    
    # Status
    is_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    admin_user = relationship("User", foreign_keys=[admin_user_id], backref="administered_society")
    members = relationship("Member", back_populates="society")
    society_members = relationship("SocietyMember", back_populates="society")
    cases = relationship("Case", back_populates="society")
    
    def __repr__(self):
        return f"<Society {self.name}>"


class SocietyMember(Base, TimestampMixin):
    """Members of a housing society"""
    __tablename__ = "society_members"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    society_id = Column(Integer, ForeignKey("societies.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Membership details
    unit_number = Column(String(50), nullable=True)
    role = Column(String(100), default="member")  # member, secretary, chairman, treasurer, etc.
    join_date = Column(Date, nullable=False)
    
    is_active = Column(Boolean, default=True)
    
    # Relationships
    society = relationship("Society", back_populates="society_members")
    user = relationship("User", backref="society_memberships")
    
    def __repr__(self):
        return f"<SocietyMember {self.user_id} @ {self.society_id}>"

