"""Publication and E-Commerce models"""
from sqlalchemy import Column, String, Text, Numeric, Integer, Boolean, ForeignKey, DateTime, Enum as SQLEnum, JSON

from sqlalchemy.orm import relationship
import uuid
import enum

from app.models.base import Base, TimestampMixin


class PublicationFormat(str, enum.Enum):
    """Publication format"""
    PRINT = "print"
    DIGITAL = "digital"
    BOTH = "both"


class PublicationCategory(str, enum.Enum):
    """Publication category"""
    LEGAL = "legal"
    RERA = "rera"
    DEEMED_CONVEYANCE = "deemed_conveyance"
    REDEVELOPMENT = "redevelopment"
    GENERAL = "general"


class OrderStatus(str, enum.Enum):
    """Order status"""
    PENDING = "pending"
    PAID = "paid"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentStatus(str, enum.Enum):
    """Payment status"""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class Publication(Base, TimestampMixin):
    """Publications (Books, Guides, Compendiums)"""
    __tablename__ = "publications"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    author = Column(String(255), nullable=False)
    isbn = Column(String(20), nullable=True, unique=True)
    
    # Pricing
    print_price = Column(Numeric(10, 2), nullable=True)
    digital_price = Column(Numeric(10, 2), nullable=True)
    format = Column(SQLEnum(PublicationFormat), nullable=False, default=PublicationFormat.BOTH)
    
    # Inventory
    stock_quantity = Column(Integer, default=0, nullable=False)
    
    # Media
    cover_image_url = Column(String(500), nullable=True)
    pdf_url = Column(String(500), nullable=True)  # For digital version
    sample_pdf_url = Column(String(500), nullable=True)  # Preview
    
    # Categorization
    category = Column(SQLEnum(PublicationCategory), nullable=False, default=PublicationCategory.GENERAL)
    tags = Column(JSON, nullable=True)  # Array of tags
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_featured = Column(Boolean, default=False, nullable=False)
    display_order = Column(Integer, default=0)
    
    # Stats
    total_sales = Column(Integer, default=0)
    views_count = Column(Integer, default=0)
    
    # Relationships
    order_items = relationship("OrderItem", back_populates="publication")
    
    def __repr__(self):
        return f"<Publication {self.title}>"


class Order(Base, TimestampMixin):
    """Customer orders"""
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    order_number = Column(String(50), unique=True, nullable=False, index=True)
    
    # Customer
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Pricing
    subtotal = Column(Numeric(10, 2), nullable=False)
    shipping_cost = Column(Numeric(10, 2), default=0, nullable=False)
    tax = Column(Numeric(10, 2), default=0, nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)
    
    # Shipping (for print books)
    shipping_address = Column(JSON, nullable=True)  # {name, address, city, state, pincode, phone}
    
    # Status
    status = Column(SQLEnum(OrderStatus), nullable=False, default=OrderStatus.PENDING)
    payment_status = Column(SQLEnum(PaymentStatus), nullable=False, default=PaymentStatus.PENDING)
    
    # Payment details
    payment_method = Column(String(50), nullable=True)  # razorpay, etc.
    payment_id = Column(String(100), nullable=True)  # External payment ID
    payment_date = Column(DateTime, nullable=True)
    
    # Tracking
    tracking_number = Column(String(100), nullable=True)
    shipped_date = Column(DateTime, nullable=True)
    delivered_date = Column(DateTime, nullable=True)
    
    # Notes
    customer_notes = Column(Text, nullable=True)
    admin_notes = Column(Text, nullable=True)
    
    # Relationships
    user = relationship("User", backref="orders")
    order_items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Order {self.order_number} - ₹{self.total_amount}>"


class OrderItem(Base, TimestampMixin):
    """Items in an order"""
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    publication_id = Column(Integer, ForeignKey("publications.id"), nullable=False)
    
    format = Column(SQLEnum(PublicationFormat), nullable=False)  # Which format was purchased
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Numeric(10, 2), nullable=False)
    subtotal = Column(Numeric(10, 2), nullable=False)
    
    # Digital delivery
    is_digital_delivered = Column(Boolean, default=False)
    digital_delivered_at = Column(DateTime, nullable=True)
    
    # Relationships
    order = relationship("Order", back_populates="order_items")
    publication = relationship("Publication", back_populates="order_items")
    
    def __repr__(self):
        return f"<OrderItem {self.publication_id} x{self.quantity}>"

