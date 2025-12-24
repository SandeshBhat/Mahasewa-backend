"""Vendor subscription models"""
from sqlalchemy import Column, String, Integer, Numeric, ForeignKey, Date, Boolean, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
import enum
from datetime import date

from app.models.base import Base, TimestampMixin


class SubscriptionTier(str, enum.Enum):
    """Subscription tier types"""
    BASIC_MONTHLY = "basic_monthly"
    BASIC_YEARLY = "basic_yearly"
    PREMIUM_MONTHLY = "premium_monthly"
    PREMIUM_YEARLY = "premium_yearly"
    ELITE_YEARLY = "elite_yearly"


class SubscriptionStatus(str, enum.Enum):
    """Subscription status"""
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    PENDING_PAYMENT = "pending_payment"


class VendorSubscriptionPlan(Base, TimestampMixin):
    """Subscription plans for vendors"""
    __tablename__ = "vendor_subscription_plans"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Plan details
    tier = Column(SQLEnum(SubscriptionTier), nullable=False, unique=True)
    name = Column(String(100), nullable=False)
    description = Column(String(1000), nullable=True)
    
    # Pricing
    base_price = Column(Numeric(10, 2), nullable=False)
    gst_rate = Column(Numeric(5, 2), default=18.00)
    total_price = Column(Numeric(10, 2), nullable=False)  # base_price + GST
    
    # Duration
    duration_months = Column(Integer, nullable=False)
    
    # Features (JSON array)
    features = Column(JSON, nullable=True)
    
    # Limits
    max_service_categories = Column(Integer, default=5)
    max_service_areas = Column(Integer, default=10)
    featured_listing = Column(Boolean, default=False)
    priority_ranking = Column(Integer, default=0)  # Higher = better ranking
    
    # Display
    is_active = Column(Boolean, default=True)
    display_order = Column(Integer, default=0)
    is_recommended = Column(Boolean, default=False)
    
    # Relationships
    subscriptions = relationship("VendorSubscription", back_populates="plan")
    
    def __repr__(self):
        return f"<VendorSubscriptionPlan {self.name} - ₹{self.total_price}>"


class VendorSubscription(Base, TimestampMixin):
    """Active subscriptions for vendors"""
    __tablename__ = "vendor_subscriptions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Vendor
    service_provider_id = Column(Integer, ForeignKey("service_providers.id", ondelete="CASCADE"), nullable=False)
    
    # Plan
    plan_id = Column(Integer, ForeignKey("vendor_subscription_plans.id"), nullable=False)
    
    # Subscription period
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    
    # Status
    status = Column(SQLEnum(SubscriptionStatus), default=SubscriptionStatus.PENDING_PAYMENT)
    
    # Payment
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True)
    paid_amount = Column(Numeric(10, 2), nullable=True)
    payment_date = Column(Date, nullable=True)
    
    # Auto-renewal
    auto_renew = Column(Boolean, default=False)
    
    # Notes
    notes = Column(String(500), nullable=True)
    
    # Relationships
    service_provider = relationship("ServiceProvider", backref="subscriptions")
    plan = relationship("VendorSubscriptionPlan", back_populates="subscriptions")
    invoice = relationship("Invoice", backref="subscription")
    
    def __repr__(self):
        return f"<VendorSubscription {self.id} - {self.status}>"
    
    @property
    def is_active(self) -> bool:
        """Check if subscription is currently active"""
        return (
            self.status == SubscriptionStatus.ACTIVE and
            self.start_date <= date.today() <= self.end_date
        )
    
    @property
    def days_remaining(self) -> int:
        """Get number of days remaining"""
        if self.end_date >= date.today():
            return (self.end_date - date.today()).days
        return 0
