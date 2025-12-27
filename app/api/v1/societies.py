"""Society management endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload, selectinload
from typing import Optional, List
from decimal import Decimal
import math

from app.db.session import get_db
from app.models.society import Society
from app.models.provider import ServiceProvider, VerificationStatus
from app.models.subscription import VendorSubscription, SubscriptionStatus, VendorSubscriptionPlan
from app.models.user import User, UserRole
from app.dependencies.auth import get_current_user
from datetime import date

router = APIRouter()


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two coordinates in kilometers (Haversine formula)"""
    if not all([lat1, lon1, lat2, lon2]):
        return None
    
    R = 6371  # Earth's radius in kilometers
    
    lat1_rad = math.radians(float(lat1))
    lat2_rad = math.radians(float(lat2))
    delta_lat = math.radians(float(lat2) - float(lat1))
    delta_lon = math.radians(float(lon2) - float(lon1))
    
    a = math.sin(delta_lat / 2) ** 2 + \
        math.cos(lat1_rad) * math.cos(lat2_rad) * \
        math.sin(delta_lon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


@router.get("/search")
async def search_societies(
    query: str = "",
    verified_only: bool = True,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """Search societies by name (for dropdowns)"""
    search_query = db.query(Society).filter(Society.is_active == True)
    
    if verified_only:
        search_query = search_query.filter(Society.is_verified == True)
    
    if query:
        search_query = search_query.filter(
            Society.name.ilike(f"%{query}%")
        )
    
    societies = search_query.order_by(Society.name).limit(limit).all()
    
    return {
        "societies": [
            {
                "id": s.id,
                "name": s.name,
                "city": s.city,
                "registration_number": s.registration_number,
                "latitude": float(s.latitude) if s.latitude else None,
                "longitude": float(s.longitude) if s.longitude else None,
            }
            for s in societies
        ],
        "total": len(societies)
    }


@router.get("/")
async def list_societies(
    skip: int = 0,
    limit: int = 100,
    verified_only: bool = False,
    active_only: bool = True,  # Default to True, but allow showing inactive
    db: Session = Depends(get_db)
):
    """List all societies"""
    query = db.query(Society)
    
    if verified_only:
        query = query.filter(Society.is_verified == True)
    
    # Only filter by active if active_only is True
    if active_only:
        query = query.filter(Society.is_active == True)
    
    societies = query.offset(skip).limit(limit).all()
    total = query.count()
    
    return {
        "societies": [
            {
                "id": s.id,
                "name": s.name,
                "registration_number": s.registration_number,
                "city": s.city,
                "address": s.address,
                "total_members": s.total_members,
                "is_verified": s.is_verified,
                "latitude": float(s.latitude) if s.latitude else None,
                "longitude": float(s.longitude) if s.longitude else None,
            }
            for s in societies
        ],
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/me")
async def get_my_society(
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's society profile
    For society_admin role, returns the society they administer
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Find society by admin_user_id (for society_admin role)
    society = db.query(Society).filter(Society.admin_user_id == current_user.id).first()
    
    if not society:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Society profile not found. Please complete your registration or contact support."
        )
    
    return {
        "id": society.id,
        "name": society.name,
        "registration_number": society.registration_number,
        "address": society.address,
        "city": society.city,
        "state": society.state,
        "pincode": society.pincode,
        "phone": society.phone,
        "email": society.email,
        "total_units": society.total_units,
        "total_members": society.total_members,
        "year_established": society.year_established,
        "registration_date": society.registration_date.isoformat() if society.registration_date else None,
        "is_verified": society.is_verified,
        "is_active": society.is_active,
        "latitude": float(society.latitude) if society.latitude else None,
        "longitude": float(society.longitude) if society.longitude else None,
        "admin_user_id": society.admin_user_id,
        "created_at": society.created_at.isoformat() if society.created_at else None,
        "updated_at": society.updated_at.isoformat() if society.updated_at else None,
    }


@router.get("/me/members")
async def get_my_society_members(
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get members of current user's society
    For society_admin role, returns all members of their society
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Find society by admin_user_id
    society = db.query(Society).filter(Society.admin_user_id == current_user.id).first()
    
    if not society:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Society profile not found"
        )
    
    # Get society members with eager loading to prevent N+1 queries
    from app.models.society import SocietyMember
    from app.models.member import Member
    
    # Get both SocietyMember and Member records for this society with eager loading
    society_members = db.query(SocietyMember).options(
        joinedload(SocietyMember.user)
    ).filter(
        SocietyMember.society_id == society.id
    ).all()
    
    members = db.query(Member).options(
        joinedload(Member.user)
    ).filter(
        Member.society_id == society.id
    ).all()
    
    # Combine and format results
    all_members = []
    
    # Add SocietyMember records (user is already loaded via eager loading)
    for sm in society_members:
        user = sm.user  # Already loaded, no additional query
        all_members.append({
            "id": sm.id,
            "user_id": sm.user_id,
            "full_name": user.full_name if user else None,
            "email": user.email if user else None,
            "mobile": user.phone if user else None,
            "unit_number": sm.unit_number,
            "designation": sm.role,
            "membership_number": None,  # SocietyMember doesn't have membership_number
            "status": "active" if sm.is_active else "inactive",
            "join_date": sm.join_date.isoformat() if sm.join_date else None,
        })
    
    # Add Member records (avoid duplicates, user is already loaded)
    existing_user_ids = {sm.user_id for sm in society_members}
    for m in members:
        if m.user_id not in existing_user_ids:
            user = m.user  # Already loaded, no additional query
            all_members.append({
                "id": m.id,
                "user_id": m.user_id,
                "full_name": user.full_name if user else None,
                "email": user.email if user else None,
                "mobile": user.phone if user else None,
                "unit_number": None,
                "designation": "member",
                "membership_number": m.membership_number,
                "status": m.status.value if m.status else "active",
                "join_date": m.join_date.isoformat() if m.join_date else None,
            })
    
    return all_members


@router.get("/me/bookings")
async def get_my_society_bookings(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    status: Optional[str] = None,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get service bookings for current user's society
    For society_admin role, returns all bookings for their society
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Find society by admin_user_id
    society = db.query(Society).filter(Society.admin_user_id == current_user.id).first()
    
    if not society:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Society profile not found"
        )
    
    # Get bookings for this society
    from app.models.booking import ServiceBooking, BookingStatus
    from app.models.provider import ServiceProvider
    
    query = db.query(ServiceBooking).filter(ServiceBooking.society_id == society.id)
    
    if status:
        try:
            status_enum = BookingStatus[status.upper()]
            query = query.filter(ServiceBooking.status == status_enum)
        except KeyError:
            pass
    
    total = query.count()
    bookings = query.order_by(ServiceBooking.created_at.desc()).offset(skip).limit(limit).all()
    
    return {
        "bookings": [
            {
                "id": b.id,
                "booking_number": b.booking_number,
                "service_id": b.service_id,
                "provider_id": b.provider_id,
                "member_id": b.member_id,
                "society_id": b.society_id,
                "service_name": b.service_name or (b.service.name if b.service else None),
                "provider_name": b.provider.business_name if b.provider else None,
                "status": b.status.value if b.status else None,
                "requested_start_date": b.requested_start_date.isoformat() if b.requested_start_date else None,
                "scheduled_date": b.scheduled_date.isoformat() if b.scheduled_date else None,
                "scheduled_time": b.scheduled_time,
                "location": b.location,
                "quote_amount": float(b.quote_amount) if b.quote_amount else None,
                "final_amount": float(b.final_amount) if b.final_amount else None,
                "payment_status": b.payment_status,
                "notes": b.notes,
                "created_at": b.created_at.isoformat() if b.created_at else None,
            }
            for b in bookings
        ],
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/{society_id}")
async def get_society(society_id: int, db: Session = Depends(get_db)):
    """Get society details"""
    society = db.query(Society).filter(Society.id == society_id).first()
    
    if not society:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Society not found"
        )
    
    return {
        "id": society.id,
        "name": society.name,
        "registration_number": society.registration_number,
        "address": society.address,
        "city": society.city,
        "state": society.state,
        "pincode": society.pincode,
        "phone": society.phone,
        "email": society.email,
        "total_members": society.total_members,
        "is_verified": society.is_verified,
        "is_active": society.is_active,
        "latitude": float(society.latitude) if society.latitude else None,
        "longitude": float(society.longitude) if society.longitude else None,
    }


@router.get("/{society_id}/nearby-vendors")
async def get_nearby_vendors(
    society_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    radius_km: Optional[int] = None,
    provider_type: Optional[str] = None,
    sort_by: Optional[str] = "priority",  # priority, distance, rating
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Get nearby vendors for a society with subscription-based priority sorting
    
    Sorting Priority:
    1. Featured/Sponsored vendors (subscription tier)
    2. Distance (closest first)
    3. Rating (highest first)
    4. Reviews count
    
    Subscription-based visibility:
    - Sponsored vendors appear first
    - Featured vendors highlighted
    """
    society = db.query(Society).filter(Society.id == society_id).first()
    
    if not society:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Society not found"
        )
    
    # Get all verified providers
    providers_query = db.query(ServiceProvider).filter(
        ServiceProvider.verification_status == VerificationStatus.VERIFIED,
        ServiceProvider.is_active == True
    )
    
    if provider_type:
        from app.models.provider import ProviderType
        try:
            pt = ProviderType[provider_type.upper()]
            providers_query = providers_query.filter(ServiceProvider.provider_type == pt)
        except KeyError:
            pass
    
    providers = providers_query.all()
    
    # Get subscription info and calculate distances
    vendors_with_metadata = []
    
    for provider in providers:
        # Get active subscription
        active_subscription = db.query(VendorSubscription).filter(
            VendorSubscription.service_provider_id == provider.id,
            VendorSubscription.status == SubscriptionStatus.ACTIVE,
            VendorSubscription.end_date >= date.today()
        ).first()
        
        subscription_tier = None
        priority_ranking = 0
        featured_listing = False
        
        if active_subscription and active_subscription.plan:
            subscription_tier = active_subscription.plan.tier.value
            priority_ranking = active_subscription.plan.priority_ranking or 0
            featured_listing = active_subscription.plan.featured_listing or False
        
        # Calculate distance if coordinates available
        distance_km = None
        if society.latitude and society.longitude and provider.latitude and provider.longitude:
            distance_km = calculate_distance(
                float(society.latitude), float(society.longitude),
                float(provider.latitude), float(provider.longitude)
            )
        
        # Filter by radius if provided
        if radius_km and distance_km and distance_km > radius_km:
            continue
        
        # If no coordinates, filter by city
        if not distance_km and society.city and provider.city:
            if society.city.lower() != provider.city.lower():
                # Check if provider serves this city
                if provider.service_areas:
                    if isinstance(provider.service_areas, list):
                        if society.city.lower() not in [area.lower() for area in provider.service_areas]:
                            continue
                    else:
                        continue
                else:
                    continue
        
        vendors_with_metadata.append({
            "provider": provider,
            "subscription_tier": subscription_tier,
            "priority_ranking": priority_ranking,
            "featured_listing": featured_listing,
            "is_sponsored": priority_ranking > 0,
            "distance_km": distance_km,
            "rating": float(provider.average_rating) if provider.average_rating else 0,
            "reviews_count": provider.total_reviews or 0
        })
    
    # Sort based on sort_by parameter
    if sort_by == "priority":
        # Sort by: Featured first, then priority_ranking, then distance, then rating
        vendors_with_metadata.sort(
            key=lambda x: (
                not x["featured_listing"],  # Featured first (False < True)
                -x["priority_ranking"],  # Higher priority first
                x["distance_km"] if x["distance_km"] is not None else 999999,  # Closer first
                -x["rating"],  # Higher rating first
                -x["reviews_count"]  # More reviews first
            )
        )
    elif sort_by == "distance" and society.latitude and society.longitude:
        # Sort by distance only
        vendors_with_metadata.sort(
            key=lambda x: x["distance_km"] if x["distance_km"] is not None else 999999
        )
    elif sort_by == "rating":
        # Sort by rating
        vendors_with_metadata.sort(
            key=lambda x: (-x["rating"], -x["reviews_count"])
        )
    
    # Apply pagination
    paginated_vendors = vendors_with_metadata[skip:skip + limit]
    
    return {
        "vendors": [
            {
                "id": item["provider"].id,
                "business_name": item["provider"].business_name,
                "provider_type": item["provider"].provider_type.value,
                "description": item["provider"].description,
                "city": item["provider"].city,
                "address": item["provider"].address,
                "phone": item["provider"].phone,
                "email": item["provider"].email,
                "website": item["provider"].website,
                "years_experience": item["provider"].years_experience,
                "average_rating": item["rating"],
                "total_reviews": item["reviews_count"],
                "subscription_tier": item["subscription_tier"],
                "is_featured": item["featured_listing"],
                "is_sponsored": item["is_sponsored"],
                "distance_km": round(item["distance_km"], 2) if item["distance_km"] else None,
                "latitude": float(item["provider"].latitude) if item["provider"].latitude else None,
                "longitude": float(item["provider"].longitude) if item["provider"].longitude else None,
            }
            for item in paginated_vendors
        ],
        "total": len(vendors_with_metadata),
        "skip": skip,
        "limit": limit,
        "sort_by": sort_by,
        "society": {
            "id": society.id,
            "name": society.name,
            "city": society.city,
            "latitude": float(society.latitude) if society.latitude else None,
            "longitude": float(society.longitude) if society.longitude else None,
        }
    }


@router.get("/me/invoices")
async def get_my_society_invoices(
    skip: int = 0,
    limit: int = 100,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current society's invoices
    
    Returns list of invoices for the logged-in society admin
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Find society by admin_user_id
    society = db.query(Society).filter(Society.admin_user_id == current_user.id).first()
    
    if not society:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Society profile not found"
        )
    
    # Get invoices using service
    from app.services.invoice_service import InvoiceService
    from app.models.invoice import Invoice
    
    invoices = InvoiceService.get_user_invoices(
        db, current_user.id, skip=skip, limit=limit
    )
    
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
        "limit": limit,
        "society": {
            "id": society.id,
            "name": society.name,
            "registration_number": society.registration_number,
        }
    }
