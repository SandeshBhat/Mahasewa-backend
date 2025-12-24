"""Content models - Blog, Events, Downloads, FAQ"""
from sqlalchemy import Column, String, Text, Integer, Boolean, ForeignKey, DateTime, Numeric, Enum as SQLEnum, JSON

from sqlalchemy.orm import relationship
import uuid
import enum

from app.models.base import Base, TimestampMixin


class BlogStatus(str, enum.Enum):
    """Blog post status"""
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class EventType(str, enum.Enum):
    """Event type"""
    WEBINAR = "webinar"
    WORKSHOP = "workshop"
    CONFERENCE = "conference"
    SEMINAR = "seminar"
    MEETING = "meeting"


class EventStatus(str, enum.Enum):
    """Event status"""
    UPCOMING = "upcoming"
    ONGOING = "ongoing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class AttendanceStatus(str, enum.Enum):
    """Attendance status"""
    REGISTERED = "registered"
    ATTENDED = "attended"
    ABSENT = "absent"
    CANCELLED = "cancelled"


class BlogPost(Base, TimestampMixin):
    """Blog posts and news articles"""
    __tablename__ = "blog_posts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    excerpt = Column(Text, nullable=True)
    content = Column(Text, nullable=False)
    
    # Author
    author_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Categorization
    category = Column(String(100), nullable=True)
    tags = Column(JSON, nullable=True)  # Array of tags
    
    # Media
    featured_image_url = Column(String(500), nullable=True)
    
    # Status & Publishing
    status = Column(SQLEnum(BlogStatus), nullable=False, default=BlogStatus.DRAFT)
    published_at = Column(DateTime, nullable=True)
    
    # SEO
    meta_description = Column(String(500), nullable=True)
    meta_keywords = Column(String(500), nullable=True)
    
    # Stats
    views_count = Column(Integer, default=0)
    is_featured = Column(Boolean, default=False)
    
    # Relationships
    author = relationship("User", backref="blog_posts")
    
    def __repr__(self):
        return f"<BlogPost {self.title} - {self.status}>"


class Event(Base, TimestampMixin):
    """Events (Webinars, Workshops, Conferences)"""
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Event details
    event_type = Column(SQLEnum(EventType), nullable=False)
    status = Column(SQLEnum(EventStatus), nullable=False, default=EventStatus.UPCOMING)
    
    # Schedule
    start_datetime = Column(DateTime, nullable=False)
    end_datetime = Column(DateTime, nullable=False)
    
    # Location
    is_online = Column(Boolean, default=False, nullable=False)
    venue = Column(String(255), nullable=True)
    venue_address = Column(Text, nullable=True)
    meeting_url = Column(String(500), nullable=True)  # For online events (Zoom, Meet, etc.)
    
    # Registration
    max_attendees = Column(Integer, nullable=True)  # NULL = unlimited
    registration_fee = Column(Numeric(10, 2), default=0, nullable=False)
    registration_deadline = Column(DateTime, nullable=True)
    is_registration_open = Column(Boolean, default=True)
    
    # Media
    banner_image_url = Column(String(500), nullable=True)
    
    # Organizer
    organizer_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Stats
    total_registrations = Column(Integer, default=0)
    total_attended = Column(Integer, default=0)
    
    # Relationships
    organizer = relationship("User", backref="organized_events")
    registrations = relationship("EventRegistration", back_populates="event", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Event {self.title} - {self.start_datetime}>"


class EventRegistration(Base, TimestampMixin):
    """Event registrations"""
    __tablename__ = "event_registrations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Registration details
    registration_date = Column(DateTime, nullable=False)
    payment_status = Column(String(50), default="pending")  # pending, completed, failed
    payment_id = Column(String(100), nullable=True)
    
    # Attendance
    attendance_status = Column(SQLEnum(AttendanceStatus), nullable=False, default=AttendanceStatus.REGISTERED)
    attended_at = Column(DateTime, nullable=True)
    
    # Feedback
    feedback = Column(Text, nullable=True)
    rating = Column(Integer, nullable=True)  # 1-5
    
    # Relationships
    event = relationship("Event", back_populates="registrations")
    user = relationship("User", backref="event_registrations")
    
    def __repr__(self):
        return f"<EventRegistration {self.user_id} -> {self.event_id}>"


class Download(Base, TimestampMixin):
    """Downloadable resources"""
    __tablename__ = "downloads"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)  # publications, circulars, magazines, templates, forms, legal-guides
    subcategory = Column(String(100), nullable=True)  # For finer categorization
    
    # File details
    file_url = Column(String(500), nullable=False)
    file_type = Column(String(50), nullable=True)  # pdf, docx, xlsx, etc.
    file_size = Column(Integer, nullable=True)  # in bytes
    cover_image_url = Column(String(500), nullable=True)  # For publications/magazines
    
    # Pricing
    is_free = Column(Boolean, default=True, nullable=False)
    price = Column(Numeric(10, 2), default=0)
    member_discount_percent = Column(Integer, default=0)
    premium_discount_percent = Column(Integer, default=0)
    
    # Access control
    access_level = Column(String(50), default='public')  # public, member, premium, paid
    requires_membership = Column(Boolean, default=False)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Stats
    download_count = Column(Integer, default=0)
    purchase_count = Column(Integer, default=0)
    total_revenue = Column(Numeric(10, 2), default=0)
    
    # Metadata
    tags = Column(JSON, nullable=True)  # Array of tags
    published_date = Column(DateTime, nullable=True)
    author = Column(String(255), nullable=True)
    language = Column(String(10), default='en')  # en, mr (Marathi)
    
    # Relationships
    download_logs = relationship("DownloadLog", back_populates="download")
    purchases = relationship("PurchaseHistory", back_populates="download")
    
    def __repr__(self):
        return f"<Download {self.title}>"


class DownloadLog(Base, TimestampMixin):
    """Track downloads"""
    __tablename__ = "download_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    download_id = Column(Integer, ForeignKey("downloads.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # NULL for anonymous
    
    downloaded_at = Column(DateTime, nullable=False)
    ip_address = Column(String(45), nullable=True)
    
    # Relationships
    download = relationship("Download", back_populates="download_logs")
    user = relationship("User", backref="download_logs")
    
    def __repr__(self):
        return f"<DownloadLog {self.download_id}>"


class PurchaseHistory(Base, TimestampMixin):
    """Track purchase history for paid downloads"""
    __tablename__ = "purchase_history"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    download_id = Column(Integer, ForeignKey("downloads.id", ondelete="CASCADE"), nullable=False)
    
    # Payment details
    amount_paid = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default='INR')
    payment_method = Column(String(50), nullable=True)  # razorpay, payu, stripe, etc.
    payment_id = Column(String(255), nullable=True)  # Payment gateway transaction ID
    payment_status = Column(String(50), default='pending')  # pending, completed, failed, refunded
    
    # Receipt
    invoice_number = Column(String(100), nullable=True)
    receipt_url = Column(String(500), nullable=True)
    
    # Access
    access_granted_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)  # NULL = lifetime access
    
    # Stats
    download_count = Column(Integer, default=0)
    last_downloaded_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", backref="purchases")
    download = relationship("Download", back_populates="purchases")
    
    def __repr__(self):
        return f"<PurchaseHistory {self.user_id} -> {self.download_id}>"


class Gallery(Base, TimestampMixin):
    """Gallery images and photos"""
    __tablename__ = "gallery"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    image_url = Column(String(500), nullable=False)
    thumbnail_url = Column(String(500), nullable=True)
    
    # Categorization
    category = Column(String(100), nullable=True)  # events, interviews, rsp, team, etc.
    album = Column(String(100), nullable=True)  # Event name, album name
    tags = Column(JSON, nullable=True)  # Array of tags
    
    # Metadata
    event_date = Column(DateTime, nullable=True)
    location = Column(String(255), nullable=True)
    photographer = Column(String(255), nullable=True)
    
    # Display
    display_order = Column(Integer, default=0)
    is_featured = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Stats
    view_count = Column(Integer, default=0)
    
    def __repr__(self):
        return f"<Gallery {self.title or self.id}>"


class FAQ(Base, TimestampMixin):
    """Frequently Asked Questions"""
    __tablename__ = "faqs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    category = Column(String(100), nullable=True)
    question = Column(String(500), nullable=False)
    answer = Column(Text, nullable=False)
    
    # Display
    display_order = Column(Integer, default=0)
    is_published = Column(Boolean, default=True, nullable=False)
    
    # Stats
    views_count = Column(Integer, default=0)
    helpful_count = Column(Integer, default=0)
    not_helpful_count = Column(Integer, default=0)
    
    def __repr__(self):
        return f"<FAQ {self.question[:50]}...>"

