"""User model with role-based access"""
from sqlalchemy import Integer
from sqlalchemy import Column, String, Boolean, DateTime, Enum as SQLEnum

import uuid
import enum

from app.models.base import Base, TimestampMixin


class UserRole(str, enum.Enum):
    """User role types"""
    SUPER_ADMIN = "super_admin"
    MAHASEWA_ADMIN = "mahasewa_admin"
    MAHASEWA_STAFF = "mahasewa_staff"
    BRANCH_MANAGER = "branch_manager"
    MAHASEWA_MEMBER = "mahasewa_member"
    SOCIETY_ADMIN = "society_admin"
    SERVICE_PROVIDER = "service_provider"
    GENERAL_USER = "general_user"


class User(Base, TimestampMixin):
    """User account"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.GENERAL_USER)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    last_login = Column(DateTime, nullable=True)
    
    # Profile fields
    avatar_url = Column(String(500), nullable=True)
    bio = Column(String(1000), nullable=True)
    
    def __repr__(self):
        return f"<User {self.email} ({self.role})>"

