"""Admin management endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import Optional, List
from datetime import datetime, timedelta
from pydantic import BaseModel

from app.db.session import get_db
from app.models.society import Society
from app.models.provider import ServiceProvider, VerificationStatus
from app.models.user import User, UserRole
from app.models.member import Member
from app.models.society import SocietyMember
from app.dependencies.auth import get_current_user
from app.models.content import Event, BlogPost
from app.models.consultation import Consultation, ConsultationStatus, ConsultationType
from app.models.invoice import Invoice

router = APIRouter()


def get_current_admin_user(
    current_user: Optional[User] = Depends(get_current_user)
):
    """Dependency to get current admin user"""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    admin_roles = ["admin", "super_admin", "mahasewa_admin"]
    if current_user.role not in admin_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return current_user


# ============ SOCIETY VERIFICATION ============

@router.post("/societies/{society_id}/verify")
async def verify_society(
    society_id: int,
    comment: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Verify a society (admin only)"""
    society = db.query(Society).filter(Society.id == society_id).first()
    
    if not society:
        raise HTTPException(status_code=404, detail="Society not found")
    
    # Update society
    society.is_verified = True
    
    if comment:
        if not society.documents:
            society.documents = {}
        society.documents["approval_comment"] = comment
    
    # Activate admin user
    if society.admin_user_id:
        admin_user = db.query(User).filter(User.id == society.admin_user_id).first()
        if admin_user:
            admin_user.is_verified = True
    
    db.commit()
    
    # Send verification email
    try:
        from app.services.email_service import EmailService
        if society.admin_user_id:
            admin_user = db.query(User).filter(User.id == society.admin_user_id).first()
            if admin_user:
                EmailService.send_society_verification_email(
                    user=admin_user,
                    society_name=society.name
                )
    except Exception as e:
        # Log error but don't fail the request
        print(f"Error sending verification email: {e}")
    
    return {
        "success": True,
        "message": f"Society '{society.name}' has been verified successfully",
        "society_id": society.id
    }


@router.post("/societies/{society_id}/reject")
async def reject_society(
    society_id: int,
    reason: Optional[str] = None,
    comment: Optional[str] = None,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Reject a society verification (admin only)"""
    from pydantic import BaseModel
    
    class RejectRequest(BaseModel):
        reason: Optional[str] = None
        comment: Optional[str] = None
    
    society = db.query(Society).filter(Society.id == society_id).first()
    
    if not society:
        raise HTTPException(status_code=404, detail="Society not found")
    
    # Update society
    society.is_verified = False
    society.is_active = False
    
    rejection_reason = reason or comment
    if rejection_reason:
        if not society.documents:
            society.documents = {}
        society.documents["rejection_reason"] = rejection_reason
        if comment:
            society.documents["rejection_comment"] = comment
    
    db.commit()
    
    # TODO: Send rejection email
    
    return {
        "success": True,
        "message": f"Society '{society.name}' has been rejected",
        "society_id": society.id
    }


# ============ VENDOR APPROVAL ============

@router.post("/providers/{provider_id}/approve")
async def approve_vendor(
    provider_id: int,
    comment: Optional[str] = None,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Approve a vendor application (admin only)"""
    provider = db.query(ServiceProvider).filter(ServiceProvider.id == provider_id).first()
    
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    # Update provider
    provider.verification_status = VerificationStatus.VERIFIED
    # Note: is_active stays False until subscription payment
    
    if comment:
        if not provider.credentials:
            provider.credentials = {}
        provider.credentials["approval_comment"] = comment
    
    db.commit()
    
    # Send approval email with subscription info
    try:
        from app.services.email_service import EmailService
        if provider.user_id:
            provider_user = db.query(User).filter(User.id == provider.user_id).first()
            if provider_user:
                EmailService.send_vendor_approval_email(
                    user=provider_user,
                    business_name=provider.business_name
                )
    except Exception as e:
        print(f"Error sending approval email: {e}")
    
    return {
        "success": True,
        "message": f"Vendor '{provider.business_name}' has been approved. They can now subscribe to a plan.",
        "provider_id": provider.id
    }


@router.post("/providers/{provider_id}/reject")
async def reject_vendor(
    provider_id: int,
    reason: Optional[str] = None,
    comment: Optional[str] = None,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Reject a vendor application (admin only)"""
    provider = db.query(ServiceProvider).filter(ServiceProvider.id == provider_id).first()
    
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    # Update provider
    provider.verification_status = VerificationStatus.REJECTED
    provider.is_active = False
    
    rejection_reason = reason or comment
    if rejection_reason:
        if not provider.credentials:
            provider.credentials = {}
        provider.credentials["rejection_reason"] = rejection_reason
        if comment:
            provider.credentials["rejection_comment"] = comment
    
    # Deactivate user
    if provider.user_id:
        user = db.query(User).filter(User.id == provider.user_id).first()
        if user:
            user.is_active = False
    
    db.commit()
    
    # TODO: Send rejection email
    
    return {
        "success": True,
        "message": f"Vendor '{provider.business_name}' has been rejected",
        "provider_id": provider.id
    }


# ============ DASHBOARD STATS ============

class DashboardStatsResponse(BaseModel):
    """Dashboard statistics response"""
    total_members: int
    total_societies: int
    total_providers: int
    events_this_month: int
    member_growth: float
    society_growth: float
    provider_growth: float
    event_growth: float
    pending_societies: int
    pending_vendors: int
    total_pending: int


class RecentActivityResponse(BaseModel):
    """Recent activity response"""
    id: str
    action: str
    user: str
    time: str
    created_at: str


class PendingTaskResponse(BaseModel):
    """Pending task response"""
    id: str
    task: str
    count: int


@router.get("/dashboard/stats/", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get comprehensive dashboard statistics"""
    
    # Current counts
    total_members = db.query(Member).filter(Member.status == "active").count()
    total_societies = db.query(Society).filter(Society.is_active == True).count()
    total_providers = db.query(ServiceProvider).filter(
        ServiceProvider.verification_status == VerificationStatus.VERIFIED
    ).count()
    
    # Events this month
    now = datetime.utcnow()
    start_of_month = datetime(now.year, now.month, 1)
    events_this_month = db.query(Event).filter(
        Event.start_datetime >= start_of_month
    ).count()
    
    # Growth calculations (comparing last 30 days to previous 30 days)
    thirty_days_ago = now - timedelta(days=30)
    sixty_days_ago = now - timedelta(days=60)
    
    # Members growth
    members_last_30 = db.query(Member).filter(
        and_(
            Member.created_at >= thirty_days_ago,
            Member.created_at < now,
            Member.status == "active"
        )
    ).count()
    members_prev_30 = db.query(Member).filter(
        and_(
            Member.created_at >= sixty_days_ago,
            Member.created_at < thirty_days_ago,
            Member.status == "active"
        )
    ).count()
    member_growth = ((members_last_30 - members_prev_30) / members_prev_30 * 100) if members_prev_30 > 0 else 0
    
    # Societies growth
    societies_last_30 = db.query(Society).filter(
        and_(
            Society.created_at >= thirty_days_ago,
            Society.created_at < now,
            Society.is_active == True
        )
    ).count()
    societies_prev_30 = db.query(Society).filter(
        and_(
            Society.created_at >= sixty_days_ago,
            Society.created_at < thirty_days_ago,
            Society.is_active == True
        )
    ).count()
    society_growth = ((societies_last_30 - societies_prev_30) / societies_prev_30 * 100) if societies_prev_30 > 0 else 0
    
    # Providers growth
    providers_last_30 = db.query(ServiceProvider).filter(
        and_(
            ServiceProvider.created_at >= thirty_days_ago,
            ServiceProvider.created_at < now,
            ServiceProvider.verification_status == VerificationStatus.VERIFIED
        )
    ).count()
    providers_prev_30 = db.query(ServiceProvider).filter(
        and_(
            ServiceProvider.created_at >= sixty_days_ago,
            ServiceProvider.created_at < thirty_days_ago,
            ServiceProvider.verification_status == VerificationStatus.VERIFIED
        )
    ).count()
    provider_growth = ((providers_last_30 - providers_prev_30) / providers_prev_30 * 100) if providers_prev_30 > 0 else 0
    
    # Events growth
    events_last_30 = db.query(Event).filter(
        and_(
            Event.start_datetime >= thirty_days_ago,
            Event.start_datetime < now
        )
    ).count()
    events_prev_30 = db.query(Event).filter(
        and_(
            Event.start_datetime >= sixty_days_ago,
            Event.start_datetime < thirty_days_ago
        )
    ).count()
    event_growth = ((events_last_30 - events_prev_30) / events_prev_30 * 100) if events_prev_30 > 0 else 0
    
    # Pending approvals
    pending_societies = db.query(Society).filter(
        and_(
            Society.is_verified == False,
            Society.is_active == True
        )
    ).count()
    
    pending_vendors = db.query(ServiceProvider).filter(
        ServiceProvider.verification_status == VerificationStatus.PENDING
    ).count()
    
    return DashboardStatsResponse(
        total_members=total_members,
        total_societies=total_societies,
        total_providers=total_providers,
        events_this_month=events_this_month,
        member_growth=round(member_growth, 1),
        society_growth=round(society_growth, 1),
        provider_growth=round(provider_growth, 1),
        event_growth=round(event_growth, 1),
        pending_societies=pending_societies,
        pending_vendors=pending_vendors,
        total_pending=pending_societies + pending_vendors
    )


@router.get("/dashboard/activities", response_model=List[RecentActivityResponse])
async def get_recent_activities(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
    limit: int = 10
):
    """Get recent activities across the platform"""
    
    activities: List[RecentActivityResponse] = []
    
    # Recent societies
    recent_societies = db.query(Society).filter(
        Society.is_active == True
    ).order_by(Society.created_at.desc()).limit(limit).all()
    
    for society in recent_societies:
        activities.append(RecentActivityResponse(
            id=f"society_{society.id}",
            action="New society registered",
            user=society.name,
            time=society.created_at.isoformat() if society.created_at else "",
            created_at=society.created_at.isoformat() if society.created_at else ""
        ))
    
    # Recent providers
    recent_providers = db.query(ServiceProvider).filter(
        ServiceProvider.verification_status == VerificationStatus.VERIFIED
    ).order_by(ServiceProvider.created_at.desc()).limit(limit).all()
    
    for provider in recent_providers:
        activities.append(RecentActivityResponse(
            id=f"provider_{provider.id}",
            action="Service provider verified",
            user=provider.business_name or "Service Provider",
            time=provider.created_at.isoformat() if provider.created_at else "",
            created_at=provider.created_at.isoformat() if provider.created_at else ""
        ))
    
    # Recent members
    recent_members = db.query(Member).join(User).filter(
        Member.status == "active"
    ).order_by(Member.created_at.desc()).limit(limit).all()
    
    for member in recent_members:
        member_name = member.user.full_name if member.user else f"Member {member.membership_number}"
        activities.append(RecentActivityResponse(
            id=f"member_{member.id}",
            action="New member added",
            user=member_name,
            time=member.created_at.isoformat() if member.created_at else "",
            created_at=member.created_at.isoformat() if member.created_at else ""
        ))
    
    # Sort by created_at descending and limit
    activities.sort(key=lambda x: x.created_at, reverse=True)
    return activities[:limit]


@router.get("/dashboard/pending-tasks", response_model=List[PendingTaskResponse])
async def get_pending_tasks(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get pending tasks requiring admin attention"""
    
    tasks = []
    
    # Pending consultations
    pending_consultations = db.query(Consultation).filter(
        Consultation.status == ConsultationStatus.PENDING
    ).count()
    
    if pending_consultations > 0:
        tasks.append({
            "id": "pending_consultations",
            "type": "consultation",
            "title": f"Review {pending_consultations} Pending Consultation(s)",
            "description": "New consultation requests require admin review and assignment",
            "priority": "high",
            "count": pending_consultations,
            "link": "/admin/consultations"
        })
    
    tasks: List[PendingTaskResponse] = []
    
    # Pending service provider verifications
    pending_providers = db.query(ServiceProvider).filter(
        ServiceProvider.verification_status == VerificationStatus.PENDING
    ).count()
    if pending_providers > 0:
        tasks.append(PendingTaskResponse(
            id="providers",
            task="Service Provider Verifications",
            count=pending_providers
        ))
    
    # Pending society registrations
    pending_societies = db.query(Society).filter(
        and_(
            Society.is_verified == False,
            Society.is_active == True
        )
    ).count()
    if pending_societies > 0:
        tasks.append(PendingTaskResponse(
            id="societies",
            task="Society Registrations",
            count=pending_societies
        ))
    
    # Upcoming events (next 7 days)
    seven_days_from_now = datetime.utcnow() + timedelta(days=7)
    upcoming_events = db.query(Event).filter(
        and_(
            Event.start_datetime >= datetime.utcnow(),
            Event.start_datetime <= seven_days_from_now
        )
    ).count()
    if upcoming_events > 0:
        tasks.append(PendingTaskResponse(
            id="events",
            task="Upcoming Events",
            count=upcoming_events
        ))
    
    return tasks


@router.get("/stats/pending")
async def get_pending_approvals(db: Session = Depends(get_db)):
    """Get count of pending approvals (legacy endpoint)"""
    
    pending_societies = db.query(Society).filter(
        and_(
            Society.is_verified == False,
            Society.is_active == True
        )
    ).count()
    
    pending_vendors = db.query(ServiceProvider).filter(
        ServiceProvider.verification_status == VerificationStatus.PENDING
    ).count()
    
    return {
        "pending_societies": pending_societies,
        "pending_vendors": pending_vendors,
        "total_pending": pending_societies + pending_vendors
    }


# ============ USER MANAGEMENT ============

class UserCreate(BaseModel):
    """Request schema for creating a user"""
    email: str
    password: str
    full_name: str
    phone: Optional[str] = None
    role: str = "general_user"
    is_active: bool = True


class UserUpdate(BaseModel):
    """Request schema for updating a user"""
    email: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


@router.get("/users/")
async def list_users(
    skip: int = 0,
    limit: int = 100,
    role: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """List all users (admin only)"""
    query = db.query(User)
    
    if role:
        try:
            role_enum = UserRole(role.lower())
            query = query.filter(User.role == role_enum)
        except ValueError:
            pass
    
    if search:
        query = query.filter(
            or_(
                User.email.ilike(f"%{search}%"),
                User.full_name.ilike(f"%{search}%")
            )
        )
    
    total = query.count()
    users = query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()
    
    return {
        "users": [
            {
                "id": u.id,
                "email": u.email,
                "full_name": u.full_name,
                "phone": u.phone,
                "role": u.role.value if u.role else None,
                "is_active": u.is_active,
                "is_verified": u.is_verified,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ],
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.post("/users")
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Create a new user (admin only)"""
    from app.utils.auth import get_password_hash
    
    # Check if user already exists
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    try:
        role_enum = UserRole(user_data.role.lower())
    except ValueError:
        role_enum = UserRole.GENERAL_USER
    
    new_user = User(
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        phone=user_data.phone,
        role=role_enum,
        is_active=user_data.is_active,
        is_verified=True  # Admin-created users are auto-verified
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {
        "success": True,
        "message": "User created successfully",
        "user": {
            "id": new_user.id,
            "email": new_user.email,
            "full_name": new_user.full_name
        }
    }


@router.put("/users/{user_id}")
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Update a user (admin only)"""
    from app.utils.auth import get_password_hash
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user_data.email is not None:
        # Check if email is already taken by another user
        existing = db.query(User).filter(User.email == user_data.email, User.id != user_id).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        user.email = user_data.email
    
    if user_data.full_name is not None:
        user.full_name = user_data.full_name
    if user_data.phone is not None:
        user.phone = user_data.phone
    if user_data.role is not None:
        try:
            user.role = UserRole(user_data.role.lower())
        except ValueError:
            pass
    if user_data.is_active is not None:
        user.is_active = user_data.is_active
    if user_data.password is not None:
        user.password_hash = get_password_hash(user_data.password)
    
    db.commit()
    db.refresh(user)
    
    return {
        "success": True,
        "message": "User updated successfully",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name
        }
    }


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Delete a user (admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent deleting yourself
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    db.delete(user)
    db.commit()
    
    return {
        "success": True,
        "message": "User deleted successfully"
    }


# ============ MEMBER MANAGEMENT ============

class MemberUpdate(BaseModel):
    """Request schema for updating a member"""
    membership_tier_id: Optional[int] = None
    status: Optional[str] = None
    join_date: Optional[str] = None
    renewal_date: Optional[str] = None
    expiry_date: Optional[str] = None
    society_id: Optional[int] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None


class MemberCreate(BaseModel):
    """Request schema for creating a member"""
    user_id: Optional[int] = None
    email: Optional[str] = None
    password: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    membership_tier_id: Optional[int] = None
    status: str = "active"
    join_date: Optional[str] = None
    renewal_date: Optional[str] = None
    expiry_date: Optional[str] = None
    society_id: Optional[int] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None


@router.post("/members")
async def create_member(
    member_data: MemberCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Create a new member (admin only)"""
    from app.models.member import Member, MembershipTier, MembershipStatus
    from app.utils.auth import get_password_hash
    from datetime import datetime, timedelta
    import random
    
    # Validate required fields
    if not member_data.user_id and not member_data.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either user_id or email (to create user) is required"
        )
    
    user_id = member_data.user_id
    
    # If email provided, create user first
    if not user_id and member_data.email:
        # Check if user exists
        existing_user = db.query(User).filter(User.email == member_data.email).first()
        if existing_user:
            user_id = existing_user.id
        else:
            # Create new user
            password = member_data.password or 'TempPassword123!'
            new_user = User(
                email=member_data.email,
                password_hash=get_password_hash(password),
                full_name=member_data.full_name or 'Member',
                phone=member_data.phone,
                role=UserRole.MAHASEWA_MEMBER,
                is_active=True,
                is_verified=True
            )
            db.add(new_user)
            db.flush()
            user_id = new_user.id
    
    # Generate membership number
    membership_number = f"MHSW{random.randint(100000, 999999)}"
    while db.query(Member).filter(Member.membership_number == membership_number).first():
        membership_number = f"MHSW{random.randint(100000, 999999)}"
    
    # Get membership tier (default to first active tier)
    membership_tier_id = member_data.membership_tier_id
    if not membership_tier_id:
        tier = db.query(MembershipTier).filter(MembershipTier.is_active == True).first()
        if not tier:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active membership tier found. Please create one first."
            )
        membership_tier_id = tier.id
    
    # Calculate dates
    join_date = datetime.now().date()
    if member_data.join_date:
        join_date = datetime.fromisoformat(member_data.join_date).date()
    
    # Get tier duration
    tier = db.query(MembershipTier).filter(MembershipTier.id == membership_tier_id).first()
    duration_months = tier.duration_months if tier else 12
    
    renewal_date = join_date + timedelta(days=365)
    expiry_date = join_date + timedelta(days=duration_months * 30)
    
    if member_data.renewal_date:
        renewal_date = datetime.fromisoformat(member_data.renewal_date).date()
    if member_data.expiry_date:
        expiry_date = datetime.fromisoformat(member_data.expiry_date).date()
    
    # Create member
    new_member = Member(
        user_id=user_id,
        membership_number=membership_number,
        membership_tier_id=membership_tier_id,
        status=MembershipStatus(member_data.status.lower()),
        join_date=join_date,
        renewal_date=renewal_date,
        expiry_date=expiry_date,
        society_id=member_data.society_id,
        address=member_data.address,
        city=member_data.city,
        state=member_data.state,
        pincode=member_data.pincode,
    )
    
    db.add(new_member)
    db.commit()
    db.refresh(new_member)
    
    return {
        "success": True,
        "message": "Member created successfully",
        "member": {
            "id": new_member.id,
            "membership_number": new_member.membership_number
        }
    }


@router.put("/members/{member_id}")
async def update_member(
    member_id: int,
    member_data: MemberUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Update a member (admin only)"""
    from app.models.member import Member, MembershipStatus
    from datetime import datetime
    
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
    
    if member_data.membership_tier_id is not None:
        member.membership_tier_id = member_data.membership_tier_id
    if member_data.status is not None:
        try:
            member.status = MembershipStatus(member_data.status.lower())
        except ValueError:
            pass
    if member_data.join_date is not None:
        member.join_date = datetime.fromisoformat(member_data.join_date).date()
    if member_data.renewal_date is not None:
        member.renewal_date = datetime.fromisoformat(member_data.renewal_date).date()
    if member_data.expiry_date is not None:
        member.expiry_date = datetime.fromisoformat(member_data.expiry_date).date()
    if member_data.society_id is not None:
        member.society_id = member_data.society_id
    if member_data.address is not None:
        member.address = member_data.address
    if member_data.city is not None:
        member.city = member_data.city
    if member_data.state is not None:
        member.state = member_data.state
    if member_data.pincode is not None:
        member.pincode = member_data.pincode
    
    db.commit()
    db.refresh(member)
    
    return {
        "success": True,
        "message": "Member updated successfully",
        "member": {
            "id": member.id,
            "membership_number": member.membership_number
        }
    }


@router.delete("/members/{member_id}")
async def delete_member(
    member_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Delete a member (admin only)"""
    from app.models.member import Member
    
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
    
    db.delete(member)
    db.commit()
    
    return {
        "success": True,
        "message": "Member deleted successfully"
    }


# ============ SOCIETY MANAGEMENT ============

class SocietyCreate(BaseModel):
    """Request schema for creating a society"""
    name: str
    registration_number: Optional[str] = None
    address: str
    city: str
    state: str
    pincode: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    total_units: Optional[int] = None
    year_established: Optional[int] = None
    is_active: bool = True


@router.post("/societies")
async def create_society(
    society_data: SocietyCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Create a new society (admin only)"""
    # Check if society with same name or registration number exists
    existing_society = db.query(Society).filter(
        (Society.name == society_data.name) |
        (Society.registration_number == society_data.registration_number)
    ).first()
    
    if existing_society:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Society with this name or registration number already exists"
        )
    
    # Create society
    new_society = Society(
        name=society_data.name,
        registration_number=society_data.registration_number,
        address=society_data.address,
        city=society_data.city,
        state=society_data.state,
        pincode=society_data.pincode,
        phone=society_data.phone,
        email=society_data.email,
        total_units=society_data.total_units,
        year_established=society_data.year_established,
        is_verified=True,  # Admin-created societies are pre-verified
        is_active=society_data.is_active
    )
    
    db.add(new_society)
    db.commit()
    db.refresh(new_society)
    
    return {
        "success": True,
        "message": "Society created successfully",
        "society": {
            "id": new_society.id,
            "name": new_society.name,
            "email": new_society.email
        }
    }


class SocietyUpdate(BaseModel):
    """Request schema for updating a society"""
    name: Optional[str] = None
    registration_number: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    total_units: Optional[int] = None
    year_established: Optional[int] = None
    is_active: Optional[bool] = None


@router.put("/societies/{society_id}")
async def update_society(
    society_id: int,
    society_data: SocietyUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Update a society (admin only)"""
    society = db.query(Society).filter(Society.id == society_id).first()
    if not society:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Society not found"
        )
    
    if society_data.name is not None:
        society.name = society_data.name
    if society_data.registration_number is not None:
        society.registration_number = society_data.registration_number
    if society_data.address is not None:
        society.address = society_data.address
    if society_data.city is not None:
        society.city = society_data.city
    if society_data.state is not None:
        society.state = society_data.state
    if society_data.pincode is not None:
        society.pincode = society_data.pincode
    if society_data.phone is not None:
        society.phone = society_data.phone
    if society_data.email is not None:
        society.email = society_data.email
    if society_data.total_units is not None:
        society.total_units = society_data.total_units
    if society_data.year_established is not None:
        society.year_established = society_data.year_established
    if society_data.is_active is not None:
        society.is_active = society_data.is_active
    
    db.commit()
    db.refresh(society)
    
    return {
        "success": True,
        "message": "Society updated successfully",
        "society": {
            "id": society.id,
            "name": society.name
        }
    }


# ============ PROVIDER MANAGEMENT ============

class ProviderCreate(BaseModel):
    """Request schema for creating a provider"""
    business_name: str
    provider_type: str
    description: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    license_number: Optional[str] = None
    years_experience: Optional[int] = None


@router.post("/providers")
async def create_provider(
    provider_data: ProviderCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Create a new provider (admin only)"""
    from app.models.provider import ServiceProvider, ProviderType, VerificationStatus
    from app.models.user import User, UserRole
    from app.utils.auth import get_password_hash
    
    # Check if email already exists
    if provider_data.email:
        existing_provider = db.query(ServiceProvider).filter(ServiceProvider.email == provider_data.email).first()
        if existing_provider:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Provider with this email already exists"
            )
    
    # Create user account for the provider
    # Generate a temporary password if not provided
    temp_password = f"Temp{provider_data.business_name.replace(' ', '')}123!"
    hashed_password = get_password_hash(temp_password)
    
    # Create user
    new_user = User(
        email=provider_data.email or f"{provider_data.business_name.lower().replace(' ', '')}@provider.local",
        password_hash=hashed_password,
        full_name=provider_data.business_name,
        phone=provider_data.phone,
        role=UserRole.SERVICE_PROVIDER,
        is_active=True,
        is_verified=True
    )
    db.add(new_user)
    db.flush()
    
    # Determine provider type
    try:
        provider_type = ProviderType(provider_data.provider_type.lower())
    except ValueError:
        provider_type = ProviderType.ADMINISTRATIVE
    
    # Create provider
    new_provider = ServiceProvider(
        user_id=new_user.id,
        business_name=provider_data.business_name,
        provider_type=provider_type,
        description=provider_data.description,
        phone=provider_data.phone,
        email=provider_data.email,
        website=provider_data.website,
        address=provider_data.address,
        city=provider_data.city,
        state=provider_data.state,
        pincode=provider_data.pincode,
        license_number=provider_data.license_number,
        years_experience=provider_data.years_experience,
        verification_status=VerificationStatus.VERIFIED,  # Admin-created providers are pre-verified
        is_active=True
    )
    
    db.add(new_provider)
    db.commit()
    db.refresh(new_provider)
    
    return {
        "success": True,
        "message": "Provider created successfully",
        "provider": {
            "id": new_provider.id,
            "business_name": new_provider.business_name,
            "email": new_provider.email
        }
    }


class ProviderUpdate(BaseModel):
    """Request schema for updating a provider"""
    business_name: Optional[str] = None
    provider_type: Optional[str] = None
    description: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    service_areas: Optional[List[str]] = None
    license_number: Optional[str] = None
    years_experience: Optional[int] = None
    is_active: Optional[bool] = None


@router.put("/providers/{provider_id}")
async def update_provider(
    provider_id: int,
    provider_data: ProviderUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Update a provider (admin only)"""
    from app.models.provider import ServiceProvider, ProviderType
    
    provider = db.query(ServiceProvider).filter(ServiceProvider.id == provider_id).first()
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found"
        )
    
    if provider_data.business_name is not None:
        provider.business_name = provider_data.business_name
    if provider_data.provider_type is not None:
        try:
            provider.provider_type = ProviderType(provider_data.provider_type.lower())
        except ValueError:
            pass
    if provider_data.description is not None:
        provider.description = provider_data.description
    if provider_data.phone is not None:
        provider.phone = provider_data.phone
    if provider_data.email is not None:
        provider.email = provider_data.email
    if provider_data.website is not None:
        provider.website = provider_data.website
    if provider_data.address is not None:
        provider.address = provider_data.address
    if provider_data.city is not None:
        provider.city = provider_data.city
    if provider_data.state is not None:
        provider.state = provider_data.state
    if provider_data.pincode is not None:
        provider.pincode = provider_data.pincode
    if provider_data.service_areas is not None:
        provider.service_areas = provider_data.service_areas
    if provider_data.license_number is not None:
        provider.license_number = provider_data.license_number
    if provider_data.years_experience is not None:
        provider.years_experience = provider_data.years_experience
    if provider_data.is_active is not None:
        # Note: ServiceProvider might not have is_active, check model
        pass
    
    db.commit()
    db.refresh(provider)
    
    return {
        "success": True,
        "message": "Provider updated successfully",
        "provider": {
            "id": provider.id,
            "business_name": provider.business_name
        }
    }
