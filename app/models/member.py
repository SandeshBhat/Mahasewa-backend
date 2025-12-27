"""Member and Membership models for MahaSeWA"""
from sqlalchemy import Column, String, Integer, Numeric, ForeignKey, Date, Boolean, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
import enum

from app.models.base import Base, TimestampMixin


class MembershipStatus(str, enum.Enum):
    """Membership status"""
    ACTIVE = "active"
    EXPIRED = "expired"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"


class MembershipTier(Base, TimestampMixin):
    """Membership tier/plan"""
    __tablename__ = "membership_tiers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(String(1000), nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    duration_months = Column(Integer, nullable=False, default=12)
    benefits = Column(JSON, nullable=True)  # JSON array of benefits
    is_active = Column(Boolean, default=True, nullable=False)
    display_order = Column(Integer, default=0)
    
    # Relationships
    members = relationship("Member", back_populates="membership_tier")
    
    def __repr__(self):
        return f"<MembershipTier {self.name} - ₹{self.price}>"


class Member(Base, TimestampMixin):
    """MahaSeWA Member (35,000+ members)"""
    __tablename__ = "members"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    membership_number = Column(String(50), unique=True, nullable=False, index=True)
    
    # Membership details
    membership_tier_id = Column(Integer, ForeignKey("membership_tiers.id"), nullable=False)
    status = Column(SQLEnum(MembershipStatus), nullable=False, default=MembershipStatus.ACTIVE)
    join_date = Column(Date, nullable=False)
    renewal_date = Column(Date, nullable=False)
    expiry_date = Column(Date, nullable=False)
    
    # Society association (optional)
    society_id = Column(Integer, ForeignKey("societies.id"), nullable=True)
    
    # Branch association
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)
    
    # Additional details
    address = Column(String(500), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    pincode = Column(String(10), nullable=True)
    
    # Relationships
    user = relationship("User", backref="member_profile")
    membership_tier = relationship("MembershipTier", back_populates="members")
    society = relationship("Society", back_populates="members")
    branch = relationship("Branch", back_populates="members")
    cases = relationship("Case", back_populates="member")
    documents = relationship("Document", back_populates="member")
    
    def __repr__(self):
        return f"<Member {self.membership_number} - {self.status}>"

