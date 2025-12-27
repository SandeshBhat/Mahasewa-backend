"""Document models for member documents"""
from sqlalchemy import Column, String, Integer, ForeignKey, Text, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum

from app.models.base import Base, TimestampMixin


class DocumentType(str, enum.Enum):
    """Document type"""
    MEMBERSHIP_CERTIFICATE = "membership_certificate"
    RECEIPT = "receipt"
    INVOICE = "invoice"
    ID_PROOF = "id_proof"
    ADDRESS_PROOF = "address_proof"
    SOCIETY_REGISTRATION = "society_registration"
    OTHER = "other"


class DocumentStatus(str, enum.Enum):
    """Document status"""
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"
    EXPIRED = "expired"


class Document(Base, TimestampMixin):
    """Member documents (certificates, receipts, etc.)"""
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Owner (member, society, or provider)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=True)
    society_id = Column(Integer, ForeignKey("societies.id"), nullable=True)
    provider_id = Column(Integer, ForeignKey("service_providers.id"), nullable=True)
    
    # Document details
    document_type = Column(SQLEnum(DocumentType), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # File details
    file_name = Column(String(255), nullable=False)
    file_url = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=True)  # in bytes
    mime_type = Column(String(100), nullable=True)
    
    # Status
    status = Column(SQLEnum(DocumentStatus), default=DocumentStatus.PENDING)
    
    # Verification
    verified_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    verification_date = Column(String(50), nullable=True)
    verification_notes = Column(Text, nullable=True)
    
    # Expiry (for documents with expiry dates)
    expiry_date = Column(String(50), nullable=True)
    
    # Metadata
    tags = Column(String(500), nullable=True)  # Comma-separated tags
    is_public = Column(Boolean, default=False)  # Can be shared/viewed by others
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="documents")
    member = relationship("Member", back_populates="documents")
    society = relationship("Society", backref="documents")
    provider = relationship("ServiceProvider", backref="documents")
    verified_by = relationship("User", foreign_keys=[verified_by_user_id], backref="verified_documents")
    
    def __repr__(self):
        return f"<Document {self.title} ({self.document_type.value})>"

