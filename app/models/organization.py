"""Organization models - Branches and Staff"""
from sqlalchemy import Integer
from sqlalchemy import Column, String, Boolean, ForeignKey, Date

from sqlalchemy.orm import relationship
import uuid

from app.models.base import Base, TimestampMixin


class Branch(Base, TimestampMixin):
    """MahaSeWA office branches"""
    __tablename__ = "branches"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    code = Column(String(20), unique=True, nullable=False)  # Branch code
    
    # Address
    address = Column(String(500), nullable=True)
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)
    pincode = Column(String(10), nullable=True)
    
    # Contact
    phone = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    
    # Manager
    manager_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    manager = relationship("User", foreign_keys=[manager_id], backref="managed_branch")
    staff_assignments = relationship("StaffAssignment", back_populates="branch")
    members = relationship("Member", back_populates="branch")
    cases = relationship("Case", back_populates="branch")
    
    def __repr__(self):
        return f"<Branch {self.name} ({self.code})>"


class StaffAssignment(Base, TimestampMixin):
    """Staff to branch assignments"""
    __tablename__ = "staff_assignments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    staff_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    
    role = Column(String(100), nullable=False)  # Case Handler, Consultant, Admin, etc.
    assigned_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)  # NULL = currently assigned
    
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    staff = relationship("User", backref="branch_assignments")
    branch = relationship("Branch", back_populates="staff_assignments")
    
    def __repr__(self):
        return f"<StaffAssignment {self.staff_user_id} @ {self.branch_id}>"

