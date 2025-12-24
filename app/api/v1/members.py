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
from app.schemas.registration import MemberRegistrationRequest, MemberRegistrationResponse
from app.services.invoice_service import InvoiceService
from app.services.email_service import EmailService
from app.dependencies.auth import get_current_user

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
        EmailService.send_member_registration_email(
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
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current member's profile"""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
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
