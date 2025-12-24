"""Service Provider models"""
from sqlalchemy import Column, String, Text, Boolean, Integer, Numeric, ForeignKey, Enum as SQLEnum, JSON

from sqlalchemy.orm import relationship
import uuid
import enum

from app.models.base import Base, TimestampMixin


class ProviderType(str, enum.Enum):
    """Provider type"""
    LEGAL = "legal"
    TECHNICAL = "technical"
    FINANCIAL = "financial"
    ADMINISTRATIVE = "administrative"


class VerificationStatus(str, enum.Enum):
    """Verification status"""
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"
    SUSPENDED = "suspended"


class ServiceProvider(Base, TimestampMixin):
    """Service Providers (MahaSeWA + Others)"""
    __tablename__ = "service_providers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    
    # Business details
    business_name = Column(String(255), nullable=False)
    provider_type = Column(SQLEnum(ProviderType), nullable=False)
    description = Column(Text, nullable=True)
    
    # Contact
    phone = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    website = Column(String(255), nullable=True)
    
    # Address
    address = Column(String(500), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    pincode = Column(String(10), nullable=True)
    
    # Location coordinates (for distance calculation)
    latitude = Column(Numeric(10, 7), nullable=True)
    longitude = Column(Numeric(10, 7), nullable=True)
    
    # Service areas (cities/areas vendor serves)
    service_areas = Column(JSON, nullable=True)  # Array of city names or area names
    
    # Service radius (based on subscription tier)
    max_service_radius_km = Column(Integer, default=10)  # Default 10km, increases with subscription
    
    # Credentials
    license_number = Column(String(100), nullable=True)
    credentials = Column(JSON, nullable=True)  # Array of certifications, licenses
    
    # Verification
    verification_status = Column(SQLEnum(VerificationStatus), default=VerificationStatus.PENDING)
    is_featured = Column(Boolean, default=False)  # MahaSeWA would be featured
    is_flagship = Column(Boolean, default=False)  # For MahaSeWA/Prabhu Associates
    
    # Experience
    years_experience = Column(Integer, nullable=True)
    total_cases_handled = Column(Integer, default=0)  # For MahaSeWA: 1000+
    
    # Ratings
    average_rating = Column(Numeric(3, 2), default=0)  # 0.00 to 5.00
    total_reviews = Column(Integer, default=0)
    
    # Media
    logo_url = Column(String(500), nullable=True)
    banner_url = Column(String(500), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Relationships
    user = relationship("User", backref="provider_profile")
    services = relationship("Service", back_populates="provider")
    
    def __repr__(self):
        return f"<ServiceProvider {self.business_name}>"


class Service(Base, TimestampMixin):
    """Services offered by providers"""
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    provider_id = Column(Integer, ForeignKey("service_providers.id", ondelete="CASCADE"), nullable=False)
    
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)
    
    # Pricing
    base_price = Column(Numeric(10, 2), nullable=True)
    price_type = Column(String(50), nullable=True)  # fixed, hourly, project-based
    
    # Details
    duration_estimate = Column(String(100), nullable=True)  # "2-3 weeks", "1 hour", etc.
    requirements = Column(JSON, nullable=True)  # Array of requirements
    
    is_active = Column(Boolean, default=True)
    
    # Relationships
    provider = relationship("ServiceProvider", back_populates="services")
    
    def __repr__(self):
        return f"<Service {self.name}>"

