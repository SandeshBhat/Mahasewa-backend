"""Member registration and management endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional

from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.society import Society, SocietyMember
from app.models.member import Member, MembershipTier, MembershipStatus
from app.models.invoice import InvoiceType
from app.models.document import Document, DocumentType, DocumentStatus
from app.schemas.registration import MemberRegistrationRequest, MemberRegistrationResponse
from app.services.invoice_service import InvoiceService
from app.services.email_service import email_service
from app.dependencies.auth import get_current_user, get_current_member_user
from pydantic import BaseModel

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.post("/register", response_model=MemberRegistrationResponse)
async def register_member(
    registration: MemberRegistrationRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new member - ALL members must be connected to a society
    
    Flow:
    1. Validate society connection (MANDATORY)
    2. Create user account with MAHASEWA_MEMBER role
    3. Handle society (select existing or create new)
    4. Create membership record (linked to society)
    5. Link to society (SocietyMember record)
    6. Generate invoice
    7. Send confirmation email
    """
    try:
        # Validate society connection - MANDATORY for all members
        if not registration.society_option:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Society connection is required. All members must be connected to a housing society."
            )
        
        if registration.society_option == "select_existing" and not registration.existing_society_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please select a society. All members must be connected to a housing society."
            )
        
        if registration.society_option == "create_new" and not registration.new_society:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New society details are required. All members must be connected to a housing society."
            )
        
        if not registration.designation:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Designation is required. Please select your designation in the society."
            )
        
        # Check if email already exists
        existing_user = db.query(User).filter(User.email == registration.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered. Please use a different email or login."
            )
        
        # 1. Create user account
        hashed_password = pwd_context.hash(registration.password)
        new_user = User(
            email=registration.email,
            password_hash=hashed_password,
            full_name=registration.full_name,
            phone=registration.mobile,
            role=UserRole.MAHASEWA_MEMBER,
            is_active=True,
            is_verified=True  # Auto-verify members
        )
        db.add(new_user)
        db.flush()  # Get user ID
        
        society_id = None
        
        # 2. Handle society - MANDATORY for all members
        if registration.society_option == "select_existing":
                # Use existing society
                if not registration.existing_society_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Society ID is required when selecting existing society"
                    )
                
                society = db.query(Society).filter(
                    Society.id == registration.existing_society_id
                ).first()
                
                if not society:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Selected society not found"
                    )
                
                society_id = society.id
                
        elif registration.society_option == "create_new":
            # Create new society
            if not registration.new_society:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="New society details are required"
                )
            
            # Check if registration number already exists
            existing_society = db.query(Society).filter(
                Society.registration_number == registration.new_society.registration_number
            ).first()
            
            if existing_society:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Society with this registration number already exists. Please select it from the list."
                )
            
            new_society = Society(
                name=registration.new_society.name,
                registration_number=registration.new_society.registration_number,
                address=registration.new_society.address or registration.address,
                city=registration.city,
                state=registration.state,
                pincode=registration.pincode,
                phone=registration.new_society.contact or registration.mobile,
                email=registration.new_society.email,
                total_units=registration.new_society.total_flats or 0,
                total_members=registration.new_society.total_members or 0,
                is_verified=False,  # Needs admin verification
                is_active=True,
                documents={
                    "total_shops": registration.new_society.total_shops,
                    "total_garages": registration.new_society.total_garages,
                    "created_by_member": new_user.id
                }
            )
            db.add(new_society)
            db.flush()
            society_id = new_society.id
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid society option. All members must be connected to a society."
            )
        
        # 3. Get or create membership tier
        tier_name = f"Individual - {registration.membership_plan.replace('year', ' Year')}"
        membership_tier = db.query(MembershipTier).filter(
            MembershipTier.name == tier_name
        ).first()
        
        if not membership_tier:
            membership_tier = MembershipTier(
                name=tier_name,
                description=f"Individual membership for {registration.membership_duration_months} months",
                price=registration.membership_base_price,
                duration_months=registration.membership_duration_months,
                benefits=[
                    "Monthly Magazine",
                    "20% Discount on Publications",
                    "Free Entry to All Seminars"
                ],
                is_active=True
            )
            db.add(membership_tier)
            db.flush()
        
        # 4. Create membership
        join_date = datetime.now().date()
        expiry_date = join_date + timedelta(days=registration.membership_duration_months * 30)
        
        membership_number = f"MEM{new_user.id:05d}{datetime.now().year}"
        
        new_membership = Member(
            user_id=new_user.id,
            membership_number=membership_number,
            membership_tier_id=membership_tier.id,
            status=MembershipStatus.ACTIVE,
            join_date=join_date,
            renewal_date=join_date,
            expiry_date=expiry_date,
            society_id=society_id,
            address=registration.address,
            city=registration.city,
            state=registration.state,
            pincode=registration.pincode
        )
        db.add(new_membership)
        db.flush()
        
        # 5. Create SocietyMember link - MANDATORY for all members
        if not society_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Society connection failed. All members must be connected to a society."
            )
        
        society_member_link = SocietyMember(
            society_id=society_id,
            user_id=new_user.id,
            role=registration.designation,
            join_date=join_date,
            is_active=True
        )
        db.add(society_member_link)
        
        # 6. Generate invoice
        from decimal import Decimal
        invoice = InvoiceService.create_membership_invoice(
            db=db,
            user=new_user,
            invoice_type=InvoiceType.MEMBERSHIP,
            base_amount=Decimal(str(registration.membership_base_price)),
            gst_rate=Decimal("18.00"),
            description=f"Individual Membership - {registration.membership_plan.replace('year', ' Year')}",
            related_type="member",
            related_id=new_membership.id,
            billing_address=registration.address
        )
        
        # 7. Send confirmation email
        from app.services.email_service import email_service
        email_service.send_member_registration_email(
            user=new_user,
            membership_number=membership_number,
            invoice=invoice,
            is_society_member=True  # All members are society members
        )
        
        message = f"Member registered successfully! Your membership number is {membership_number}."
        if registration.society_option == "create_new":
            message += " Your society registration is pending admin verification."
        
        return MemberRegistrationResponse(
            success=True,
            message=f"{message} Invoice #{invoice.invoice_number} has been generated.",
            member_id=new_membership.id,
            user_id=new_user.id,
            society_id=society_id,
            membership_id=new_membership.id,
            invoice_id=invoice.id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@router.get("/me")
async def get_my_member_profile(
    current_user: User = Depends(get_current_member_user),
    db: Session = Depends(get_db)
):
    """Get current member's profile"""
    
    # Find member by user_id with eager loading to prevent N+1 queries
    from sqlalchemy.orm import joinedload
    
    member = db.query(Member).options(
        joinedload(Member.society),
        joinedload(Member.user)
    ).filter(Member.user_id == current_user.id).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member profile not found. Please complete your registration."
        )
    
    # Get society if linked (already loaded via eager loading)
    society = member.society  # Already loaded, no additional query
    
    return {
        "member": {
            "id": member.id,
            "membership_number": member.membership_number,
            "user_id": member.user_id,
            "society_id": member.society_id,
            "membership_tier": member.membership_tier.value if member.membership_tier else None,
            "status": member.status.value if member.status else None,
            "membership_status": member.status.value if member.status else None,
            "join_date": member.join_date.isoformat() if member.join_date else None,
            "renewal_date": member.renewal_date.isoformat() if member.renewal_date else None,
            "expiry_date": member.expiry_date.isoformat() if member.expiry_date else None,
            "created_at": member.created_at.isoformat() if member.created_at else None,
            "user": {
                "id": current_user.id,
                "email": current_user.email,
                "full_name": current_user.full_name,
                "phone": current_user.phone,
            },
            "society": {
                "id": society.id,
                "name": society.name,
                "registration_number": society.registration_number,
                "city": society.city,
            } if society else None
        }
    }


@router.get("/")
async def list_members(
    skip: int = 0,
    limit: int = 100,
    society_id: int = None,
    active_only: bool = True,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all members"""
    from app.models.user import User
    
    query = db.query(Member)
    
    if society_id:
        query = query.filter(Member.society_id == society_id)
    
    if active_only:
        query = query.filter(Member.status == MembershipStatus.ACTIVE)
    
    # Search by email or name if provided
    if search:
        query = query.join(User).filter(
            or_(
                User.email.ilike(f"%{search}%"),
                User.full_name.ilike(f"%{search}%")
            )
        )
    
    members = query.offset(skip).limit(limit).all()
    total = query.count()
    
    return {
        "members": [
            {
                "id": m.id,
                "membership_number": m.membership_number,
                "user_email": m.user.email,
                "full_name": m.user.full_name,
                "status": m.status.value,
                "join_date": m.join_date.isoformat(),
                "expiry_date": m.expiry_date.isoformat()
            }
            for m in members
        ],
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/me/invoices")
async def get_my_member_invoices(
    skip: int = 0,
    limit: int = 100,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current member's invoices
    
    Returns list of invoices for the logged-in member
    """
    # Verify member exists
    member = db.query(Member).filter(Member.user_id == current_user.id).first()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member profile not found"
        )
    
    # Get invoices using service
    invoices = InvoiceService.get_user_invoices(
        db, current_user.id, skip=skip, limit=limit
    )
    
    from app.models.invoice import Invoice
    total = db.query(Invoice).filter(Invoice.user_id == current_user.id).count()
    
    return {
        "invoices": [
            {
                "id": inv.id,
                "invoice_number": inv.invoice_number,
                "invoice_type": inv.invoice_type.value,
                "invoice_date": inv.invoice_date.isoformat(),
                "due_date": inv.due_date.isoformat() if inv.due_date else None,
                "total_amount": float(inv.total_amount),
                "status": inv.status.value,
                "payment_date": inv.payment_date.isoformat() if inv.payment_date else None,
            }
            for inv in invoices
        ],
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/me/bookings")
async def get_my_member_bookings(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_member_user),
    db: Session = Depends(get_db)
):
    """
    Get current member's service bookings
    
    Returns list of bookings made by the logged-in member
    """
    
    # Verify member exists
    member = db.query(Member).filter(Member.user_id == current_user.id).first()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member profile not found"
        )
    
    # Get bookings
    from app.models.booking import Booking, BookingStatus
    from sqlalchemy.orm import joinedload
    
    query = db.query(Booking).options(
        joinedload(Booking.provider)
    ).filter(Booking.user_id == current_user.id)
    
    # Filter by status if provided
    if status_filter:
        try:
            status_enum = BookingStatus[status_filter.upper()]
            query = query.filter(Booking.status == status_enum)
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_filter}"
            )
    
    total = query.count()
    bookings = query.order_by(Booking.created_at.desc()).offset(skip).limit(limit).all()
    
    return {
        "bookings": [
            {
                "id": b.id,
                "service_name": b.service_name,
                "service_category": b.service_category,
                "provider_id": b.provider_id,
                "provider_name": b.provider.business_name if b.provider else None,
                "scheduled_date": b.scheduled_date.isoformat() if b.scheduled_date else None,
                "scheduled_time": b.scheduled_time,
                "status": b.status.value,
                "total_cost": float(b.total_cost) if b.total_cost else None,
                "notes": b.notes,
                "created_at": b.created_at.isoformat() if b.created_at else None,
            }
            for b in bookings
        ],
        "total": total,
        "skip": skip,
        "limit": limit
    }


# ============ DOCUMENT MANAGEMENT ============

class DocumentCreate(BaseModel):
    """Request schema for creating a document"""
    document_type: str
    title: str
    description: Optional[str] = None
    file_name: str
    file_url: str
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    expiry_date: Optional[str] = None
    tags: Optional[str] = None
    is_public: bool = False


class DocumentUpdate(BaseModel):
    """Request schema for updating a document"""
    title: Optional[str] = None
    description: Optional[str] = None
    expiry_date: Optional[str] = None
    tags: Optional[str] = None
    is_public: Optional[bool] = None


@router.get("/me/documents")
async def get_my_member_documents(
    skip: int = 0,
    limit: int = 100,
    document_type: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_member_user),
    db: Session = Depends(get_db)
):
    """
    Get current member's documents
    
    Returns list of documents uploaded by or issued to the member
    (e.g., membership certificates, receipts, etc.)
    """
    
    # Verify member exists
    member = db.query(Member).filter(Member.user_id == current_user.id).first()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member profile not found"
        )
    
    # Query documents
    query = db.query(Document).filter(Document.member_id == member.id)
    
    # Apply filters
    if document_type:
        try:
            doc_type = DocumentType(document_type)
            query = query.filter(Document.document_type == doc_type)
        except ValueError:
            pass
    
    if status:
        try:
            doc_status = DocumentStatus(status)
            query = query.filter(Document.status == doc_status)
        except ValueError:
            pass
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    documents = query.order_by(Document.created_at.desc()).offset(skip).limit(limit).all()
    
    return {
        "documents": [
            {
                "id": doc.id,
                "document_type": doc.document_type.value,
                "title": doc.title,
                "description": doc.description,
                "file_name": doc.file_name,
                "file_url": doc.file_url,
                "file_size": doc.file_size,
                "mime_type": doc.mime_type,
                "status": doc.status.value,
                "expiry_date": doc.expiry_date,
                "tags": doc.tags.split(",") if doc.tags else [],
                "is_public": doc.is_public,
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
                "verified_by": doc.verified_by_user_id,
                "verification_date": doc.verification_date,
            }
            for doc in documents
        ],
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.post("/me/documents")
async def create_member_document(
    document_data: DocumentCreate,
    current_user: User = Depends(get_current_member_user),
    db: Session = Depends(get_db)
):
    """Upload a new document for the current member"""
    
    # Verify member exists
    member = db.query(Member).filter(Member.user_id == current_user.id).first()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member profile not found"
        )
    
    # Validate document type
    try:
        doc_type = DocumentType(document_data.document_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid document type. Valid types: {[e.value for e in DocumentType]}"
        )
    
    # Create document
    new_document = Document(
        user_id=current_user.id,
        member_id=member.id,
        document_type=doc_type,
        title=document_data.title,
        description=document_data.description,
        file_name=document_data.file_name,
        file_url=document_data.file_url,
        file_size=document_data.file_size,
        mime_type=document_data.mime_type,
        expiry_date=document_data.expiry_date,
        tags=document_data.tags,
        is_public=document_data.is_public,
        status=DocumentStatus.PENDING
    )
    
    db.add(new_document)
    db.commit()
    db.refresh(new_document)
    
    return {
        "success": True,
        "message": "Document uploaded successfully",
        "document": {
            "id": new_document.id,
            "document_type": new_document.document_type.value,
            "title": new_document.title,
            "file_url": new_document.file_url,
            "status": new_document.status.value,
            "created_at": new_document.created_at.isoformat() if new_document.created_at else None,
        }
    }


@router.put("/me/documents/{document_id}")
async def update_member_document(
    document_id: int,
    document_data: DocumentUpdate,
    current_user: User = Depends(get_current_member_user),
    db: Session = Depends(get_db)
):
    """Update a member's document"""
    
    # Verify member exists
    member = db.query(Member).filter(Member.user_id == current_user.id).first()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member profile not found"
        )
    
    # Get document
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.member_id == member.id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Update fields
    if document_data.title is not None:
        document.title = document_data.title
    if document_data.description is not None:
        document.description = document_data.description
    if document_data.expiry_date is not None:
        document.expiry_date = document_data.expiry_date
    if document_data.tags is not None:
        document.tags = document_data.tags
    if document_data.is_public is not None:
        document.is_public = document_data.is_public
    
    db.commit()
    db.refresh(document)
    
    return {
        "success": True,
        "message": "Document updated successfully",
        "document": {
            "id": document.id,
            "title": document.title,
            "status": document.status.value,
        }
    }


@router.delete("/me/documents/{document_id}")
async def delete_member_document(
    document_id: int,
    current_user: User = Depends(get_current_member_user),
    db: Session = Depends(get_db)
):
    """Delete a member's document"""
    
    # Verify member exists
    member = db.query(Member).filter(Member.user_id == current_user.id).first()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member profile not found"
        )
    
    # Get document
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.member_id == member.id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Delete document (file deletion should be handled by file storage service)
    db.delete(document)
    db.commit()
    
    return {
        "success": True,
        "message": "Document deleted successfully"
    }
