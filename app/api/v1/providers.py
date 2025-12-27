"""Service provider/vendor registration and management endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload, selectinload
from passlib.context import CryptContext
from typing import Optional, List
from decimal import Decimal
import math

from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.provider import ServiceProvider, Service, VerificationStatus, ProviderType
from app.models.society import Society
from app.models.subscription import VendorSubscription, SubscriptionStatus, SubscriptionTier
from app.schemas.registration import VendorRegistrationRequest, VendorRegistrationResponse
from datetime import date

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Email service imported where needed

# Import auth dependency
try:
    from app.dependencies.auth import get_current_user
except ImportError:
    try:
        from app.core.dependencies import get_current_user
    except ImportError:
        # Fallback for when auth dependency is not available
        async def get_current_user():
            return None


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


def get_subscription_radius_km(subscription_tier: Optional[str]) -> int:
    """Get service radius based on subscription tier"""
    if not subscription_tier:
        return 10  # Default: 10km
    
    tier_radius_map = {
        'basic_monthly': 10,
        'basic_yearly': 10,
        'premium_monthly': 25,
        'premium_yearly': 25,
        'elite_yearly': 999999  # No limit (all areas)
    }
    
    return tier_radius_map.get(subscription_tier, 10)


@router.post("/register", response_model=VendorRegistrationResponse)
async def register_vendor(
    registration: VendorRegistrationRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new vendor/service provider
    
    Flow:
    1. Create user account with SERVICE_PROVIDER role
    2. Create service_provider record (status: pending_approval)
    3. Create service records for each category
    4. Send registration confirmation email
    5. Admin will review and approve/reject
    
    Note: Subscription is handled separately after admin approval
    """
    try:
        # Check if email already exists
        existing_user = db.query(User).filter(User.email == registration.account_email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered. Please use a different email or login."
            )
        
        # Check if business email exists
        existing_provider = db.query(ServiceProvider).filter(
            ServiceProvider.email == registration.business.email
        ).first()
        if existing_provider:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Business email already registered."
            )
        
        # 1. Create user account
        hashed_password = pwd_context.hash(registration.account_password)
        new_user = User(
            email=registration.account_email,
            password_hash=hashed_password,
            full_name=registration.business.owner_name,
            phone=registration.business.phone,
            role=UserRole.SERVICE_PROVIDER,
            is_active=False,  # Inactive until admin approves
            is_verified=False
        )
        db.add(new_user)
        db.flush()  # Get user ID
        
        # 2. Determine provider type based on services
        # Default to ADMINISTRATIVE, can be updated by admin
        provider_type = ProviderType.ADMINISTRATIVE
        if any(cat in ["Legal Services", "CA", "Accounting Services"] for cat in registration.services.categories):
            provider_type = ProviderType.LEGAL
        elif any(cat in ["Architect", "Engineer", "Architectural Services", "Engineering Services"] for cat in registration.services.categories):
            provider_type = ProviderType.TECHNICAL
        elif any(cat in ["Accounting Services", "CA"] for cat in registration.services.categories):
            provider_type = ProviderType.FINANCIAL
        
        # 3. Geocode address to get coordinates (background task, don't block registration)
        latitude = None
        longitude = None
        if registration.business.address:
            try:
                from app.services.geocoding_service import geocoding_service
                # Note: Geocoding is async but we'll do it synchronously here
                # In production, consider using background tasks
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                coordinates = loop.run_until_complete(
                    geocoding_service.geocode_address(
                        address=registration.business.address,
                        city=registration.business.city,
                        state=registration.business.state,
                        pincode=registration.business.pincode
                    )
                )
                if coordinates:
                    latitude, longitude = coordinates
            except Exception as e:
                # Log but don't fail registration if geocoding fails
                print(f"Geocoding failed for provider registration: {e}")
        
        # 4. Create service provider
        new_provider = ServiceProvider(
            user_id=new_user.id,
            business_name=registration.business.name,
            provider_type=provider_type,
            description=registration.services.description,
            phone=registration.business.phone,
            email=registration.business.email,
            website=registration.business.website,
            address=registration.business.address,
            city=registration.business.city,
            state=registration.business.state,
            pincode=registration.business.pincode,
            latitude=latitude,
            longitude=longitude,
            verification_status=VerificationStatus.PENDING,
            is_active=False,  # Inactive until admin approves
            max_service_radius_km=10  # Default radius
        )
        db.add(new_provider)
        db.flush()  # Get provider ID
        
        # 5. Create services
        for category in registration.services.categories:
            service = Service(
                provider_id=new_provider.id,
                name=category,
                category=category,
                description=f"{category} service",
                is_active=True
            )
            db.add(service)
        
        db.commit()
        db.refresh(new_provider)
        
        # Send registration confirmation email
        try:
            from app.services.email_service import email_service
            email_service.send_registration_confirmation_email(
                user=new_user,
                role="service_provider"
            )
        except Exception as e:
            # Log error but don't fail the request
            print(f"Error sending registration email: {e}")
        
        return VendorRegistrationResponse(
            success=True,
            message="Registration submitted successfully. Your account will be activated after admin approval.",
            provider_id=new_provider.id,
            user_id=new_user.id
        )
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@router.get("/")
async def list_providers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    verified_only: bool = False,
    provider_type: Optional[str] = None,
    city: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    sort_by: Optional[str] = "priority",  # priority, distance, rating
    db: Session = Depends(get_db)
):
    """
    List all service providers with subscription-based priority sorting
    
    Sorting options:
    - priority: Subscription tier first, then distance, then rating
    - distance: Closest first (requires latitude/longitude)
    - rating: Highest rating first
    """
    query = db.query(ServiceProvider)
    
    if verified_only:
        query = query.filter(ServiceProvider.verification_status == VerificationStatus.VERIFIED)
    
    if provider_type:
        try:
            pt = ProviderType[provider_type.upper()]
            query = query.filter(ServiceProvider.provider_type == pt)
        except KeyError:
            pass
    
    if city:
        query = query.filter(ServiceProvider.city.ilike(f"%{city}%"))
    
    query = query.filter(ServiceProvider.is_active == True)
    
    providers = query.all()
    total = len(providers)
    
    # Pre-fetch all subscriptions for providers to avoid N+1 queries
    provider_ids = [p.id for p in providers]
    all_subscriptions = db.query(VendorSubscription).options(
        joinedload(VendorSubscription.plan)
    ).filter(
        VendorSubscription.service_provider_id.in_(provider_ids),
        VendorSubscription.status == SubscriptionStatus.ACTIVE,
        VendorSubscription.end_date >= date.today()
    ).all()
    
    # Create a map of provider_id -> active subscription
    subscriptions_map = {sub.service_provider_id: sub for sub in all_subscriptions}
    
    # Get subscription info and calculate distances
    from app.models.subscription import VendorSubscriptionPlan
    
    providers_with_metadata = []
    for p in providers:
        # Get active subscription from pre-fetched map (no additional query)
        active_subscription = subscriptions_map.get(p.id)
        
        subscription_status = "none"
        priority_ranking = 0
        featured_listing = False
        
        if active_subscription and active_subscription.plan:
            subscription_status = active_subscription.plan.tier.value
            priority_ranking = active_subscription.plan.priority_ranking or 0
            featured_listing = active_subscription.plan.featured_listing or False
        
        # Calculate distance if coordinates provided
        distance_km = None
        if latitude and longitude and p.latitude and p.longitude:
            distance_km = calculate_distance(
                float(latitude), float(longitude),
                float(p.latitude), float(p.longitude)
            )
        
        providers_with_metadata.append({
            "provider": p,
            "subscription_status": subscription_status,
            "priority_ranking": priority_ranking,
            "featured_listing": featured_listing,
            "distance_km": distance_km,
            "rating": float(p.average_rating) if p.average_rating else 0,
            "reviews_count": p.total_reviews or 0
        })
    
    # Sort based on sort_by parameter
    if sort_by == "priority":
        # Sort by: Featured first, then priority_ranking, then distance, then rating
        providers_with_metadata.sort(
            key=lambda x: (
                not x["featured_listing"],  # Featured first (False < True)
                -x["priority_ranking"],  # Higher priority first
                x["distance_km"] if x["distance_km"] is not None else 999999,  # Closer first
                -x["rating"],  # Higher rating first
                -x["reviews_count"]  # More reviews first
            )
        )
    elif sort_by == "distance" and latitude and longitude:
        # Sort by distance only
        providers_with_metadata.sort(
            key=lambda x: x["distance_km"] if x["distance_km"] is not None else 999999
        )
    elif sort_by == "rating":
        # Sort by rating
        providers_with_metadata.sort(
            key=lambda x: (-x["rating"], -x["reviews_count"])
        )
    
    # Apply pagination
    paginated_providers = providers_with_metadata[skip:skip + limit]
    
    providers_list = []
    for item in paginated_providers:
        p = item["provider"]
        providers_list.append({
            "id": p.id,
            "business_name": p.business_name,
            "provider_type": p.provider_type.value,
            "city": p.city,
            "verification_status": p.verification_status.value,
            "years_experience": p.years_experience,
            "average_rating": float(p.average_rating) if p.average_rating else 0,
            "total_reviews": p.total_reviews or 0,
            "subscription_status": item["subscription_status"],
            "is_featured": item["featured_listing"],
            "is_sponsored": item["priority_ranking"] > 0,
            "distance_km": round(item["distance_km"], 2) if item["distance_km"] else None,
            "latitude": float(p.latitude) if p.latitude else None,
            "longitude": float(p.longitude) if p.longitude else None,
        })
    
    return {
        "providers": providers_list,
        "total": total,
        "skip": skip,
        "limit": limit,
        "sort_by": sort_by
    }


@router.get("/me/nearby-societies")
async def get_nearby_societies(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    radius_km: Optional[int] = None,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get nearby societies for current vendor based on location and subscription tier
    
    Subscription-based radius:
    - Basic: 10km
    - Premium: 25km
    - Elite: No limit (all societies)
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    if current_user.role != UserRole.SERVICE_PROVIDER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Service provider role required."
        )
    
    provider = db.query(ServiceProvider).filter(ServiceProvider.user_id == current_user.id).first()
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider profile not found"
        )
    
    # Get subscription tier
    active_subscription = db.query(VendorSubscription).filter(
        VendorSubscription.service_provider_id == provider.id,
        VendorSubscription.status == SubscriptionStatus.ACTIVE,
        VendorSubscription.end_date >= date.today()
    ).first()
    
    subscription_tier = active_subscription.plan.tier.value if active_subscription and active_subscription.plan else None
    max_radius = get_subscription_radius_km(subscription_tier)
    
    # Use provided radius or subscription-based radius
    search_radius = radius_km if radius_km else max_radius
    
    # Get all verified societies
    societies_query = db.query(Society).filter(
        Society.is_verified == True,
        Society.is_active == True
    )
    
    # If provider has location, filter by distance
    if provider.latitude and provider.longitude:
        societies = societies_query.all()
        nearby_societies = []
        
        for society in societies:
            if society.latitude and society.longitude:
                distance = calculate_distance(
                    float(provider.latitude), float(provider.longitude),
                    float(society.latitude), float(society.longitude)
                )
                
                if distance is not None and distance <= search_radius:
                    nearby_societies.append({
                        "society": society,
                        "distance_km": distance
                    })
            else:
                # If society has no coordinates, include if same city
                if society.city and provider.city and society.city.lower() == provider.city.lower():
                    nearby_societies.append({
                        "society": society,
                        "distance_km": None
                    })
        
        # Sort by distance
        nearby_societies.sort(key=lambda x: x["distance_km"] if x["distance_km"] is not None else 999999)
        
        # Apply pagination
        paginated = nearby_societies[skip:skip + limit]
        
        return {
            "societies": [
                {
                    "id": s["society"].id,
                    "name": s["society"].name,
                    "city": s["society"].city,
                    "address": s["society"].address,
                    "registration_number": s["society"].registration_number,
                    "total_members": s["society"].total_members,
                    "distance_km": round(s["distance_km"], 2) if s["distance_km"] else None,
                    "latitude": float(s["society"].latitude) if s["society"].latitude else None,
                    "longitude": float(s["society"].longitude) if s["society"].longitude else None,
                }
                for s in paginated
            ],
            "total": len(nearby_societies),
            "skip": skip,
            "limit": limit,
            "subscription_tier": subscription_tier,
            "max_radius_km": max_radius,
            "search_radius_km": search_radius
        }
    else:
        # No location - filter by city only
        if provider.city:
            societies_query = societies_query.filter(Society.city.ilike(f"%{provider.city}%"))
        
        societies = societies_query.offset(skip).limit(limit).all()
        total = societies_query.count()
        
        return {
            "societies": [
                {
                    "id": s.id,
                    "name": s.name,
                    "city": s.city,
                    "address": s.address,
                    "registration_number": s.registration_number,
                    "total_members": s.total_members,
                    "distance_km": None,
                    "latitude": float(s.latitude) if s.latitude else None,
                    "longitude": float(s.longitude) if s.longitude else None,
                }
                for s in societies
            ],
            "total": total,
            "skip": skip,
            "limit": limit,
            "subscription_tier": subscription_tier,
            "max_radius_km": max_radius,
            "search_radius_km": search_radius,
            "note": "Provider location not set - showing societies in same city"
        }


@router.get("/{provider_id}")
async def get_provider(provider_id: int, db: Session = Depends(get_db)):
    """Get provider details"""
    provider = db.query(ServiceProvider).filter(ServiceProvider.id == provider_id).first()
    
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found"
        )
    
    # Get services
    services = db.query(Service).filter(Service.provider_id == provider_id).all()
    
    return {
        "id": provider.id,
        "business_name": provider.business_name,
        "provider_type": provider.provider_type.value,
        "description": provider.description,
        "phone": provider.phone,
        "email": provider.email,
        "website": provider.website,
        "address": provider.address,
        "city": provider.city,
        "state": provider.state,
        "pincode": provider.pincode,
        "verification_status": provider.verification_status.value,
        "years_experience": provider.years_experience,
        "average_rating": float(provider.average_rating) if provider.average_rating else 0,
        "total_reviews": provider.total_reviews,
        "credentials": provider.credentials,
        "latitude": float(provider.latitude) if provider.latitude else None,
        "longitude": float(provider.longitude) if provider.longitude else None,
        "service_areas": provider.service_areas,
        "max_service_radius_km": provider.max_service_radius_km,
        "services": [
            {
                "id": s.id,
                "name": s.name,
                "category": s.category,
                "description": s.description
            }
            for s in services
        ]
    }


# ============ PROVIDER DASHBOARD ENDPOINTS ============

@router.get("/me/profile")
async def get_my_provider_profile(
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current provider's own profile"""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    if current_user.role != UserRole.SERVICE_PROVIDER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Service provider role required."
        )
    
    provider = db.query(ServiceProvider).filter(ServiceProvider.user_id == current_user.id).first()
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider profile not found. Please complete your registration."
        )
    
    # Get services
    services = db.query(Service).filter(Service.provider_id == provider.id).all()
    
    # Get subscription info
    active_subscription = db.query(VendorSubscription).filter(
        VendorSubscription.service_provider_id == provider.id,
        VendorSubscription.status == SubscriptionStatus.ACTIVE,
        VendorSubscription.end_date >= date.today()
    ).first()
    
    subscription_tier = active_subscription.plan.tier.value if active_subscription and active_subscription.plan else None
    max_radius = get_subscription_radius_km(subscription_tier)
    
    return {
        "id": provider.id,
        "business_name": provider.business_name,
        "provider_type": provider.provider_type.value,
        "description": provider.description,
        "phone": provider.phone,
        "email": provider.email,
        "website": provider.website,
        "address": provider.address,
        "city": provider.city,
        "state": provider.state,
        "pincode": provider.pincode,
        "verification_status": provider.verification_status.value,
        "years_experience": provider.years_experience,
        "average_rating": float(provider.average_rating) if provider.average_rating else 0,
        "total_reviews": provider.total_reviews,
        "credentials": provider.credentials,
        "latitude": float(provider.latitude) if provider.latitude else None,
        "longitude": float(provider.longitude) if provider.longitude else None,
        "service_areas": provider.service_areas,
        "max_service_radius_km": provider.max_service_radius_km,
        "subscription_tier": subscription_tier,
        "subscription_radius_km": max_radius,
        "services": [
            {
                "id": s.id,
                "name": s.name,
                "category": s.category,
                "description": s.description,
                "base_price": float(s.base_price) if s.base_price else None,
                "is_active": s.is_active
            }
            for s in services
        ]
    }


@router.put("/me/profile")
async def update_my_provider_profile(
    profile_data: dict,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current provider's profile"""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    if current_user.role != UserRole.SERVICE_PROVIDER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Service provider role required."
        )
    
    provider = db.query(ServiceProvider).filter(ServiceProvider.user_id == current_user.id).first()
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider profile not found"
        )
    
    # Update allowed fields
    allowed_fields = [
        "description", "phone", "email", "website", "address", 
        "city", "state", "pincode", "latitude", "longitude",
        "service_areas", "credentials"
    ]
    
    for field in allowed_fields:
        if field in profile_data:
            setattr(provider, field, profile_data[field])
    
    db.commit()
    db.refresh(provider)
    
    return {
        "success": True,
        "message": "Profile updated successfully",
        "provider": {
            "id": provider.id,
            "business_name": provider.business_name
        }
    }


@router.get("/me/bookings")
async def get_my_bookings(
    skip: int = 0,
    limit: int = 100,
    booking_status: Optional[str] = None,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current provider's bookings"""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    if current_user.role != UserRole.SERVICE_PROVIDER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Service provider role required."
        )
    
    provider = db.query(ServiceProvider).filter(ServiceProvider.user_id == current_user.id).first()
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider profile not found"
        )
    
    # Import here to avoid circular dependency
    from app.models.booking import ServiceBooking, BookingStatus
    
    query = db.query(ServiceBooking).filter(ServiceBooking.provider_id == provider.id)
    
    if booking_status:
        try:
            status_enum = BookingStatus[booking_status.upper()]
            query = query.filter(ServiceBooking.status == status_enum)
        except KeyError:
            pass
    
    total = query.count()
    bookings = query.order_by(ServiceBooking.created_at.desc()).offset(skip).limit(limit).all()
    
    # Get subscription info for area filtering
    active_subscription = db.query(VendorSubscription).filter(
        VendorSubscription.service_provider_id == provider.id,
        VendorSubscription.status == SubscriptionStatus.ACTIVE,
        VendorSubscription.end_date >= date.today()
    ).first()
    
    subscription_tier = active_subscription.plan.tier.value if active_subscription and active_subscription.plan else None
    can_see_wider_area = subscription_tier in ['premium_monthly', 'premium_yearly', 'elite_yearly'] if subscription_tier else False
    
    # Filter bookings by area if not premium/elite
    filtered_bookings = bookings
    if not can_see_wider_area and provider.city:
        # Only show bookings from same city
        filtered_bookings = []
        for b in bookings:
            if b.society_id:
                society = db.query(Society).filter(Society.id == b.society_id).first()
                if society and society.city and society.city.lower() == provider.city.lower():
                    filtered_bookings.append(b)
            else:
                # If no society, include it (individual bookings)
                filtered_bookings.append(b)
        total = len(filtered_bookings)
    
    return {
        "bookings": [
            {
                "id": b.id,
                "booking_number": b.booking_number,
                "service_id": b.service_id,
                "member_id": b.member_id,
                "service_name": b.service_name,
                "description": b.description,
                "requested_start_date": b.requested_start_date.isoformat() if b.requested_start_date else None,
                "status": b.status.value,
                "quote_amount": float(b.quote_amount) if b.quote_amount else None,
                "final_amount": float(b.final_amount) if b.final_amount else None,
                "payment_status": b.payment_status,
                "service_name_display": b.service.name if b.service else b.service_name,
                "customer_name": b.client.full_name if b.client else None,
                "customer_email": b.client.email if b.client else None,
                "customer_phone": b.client.phone if b.client else None,
                # Society info (only visible after booking is made)
                "society_name": b.society.name if b.society else None,
                "society_city": b.society.city if b.society else None,
                "society_address": b.society.address if b.society else None,
                "created_at": b.created_at.isoformat() if b.created_at else None,
            }
            for b in filtered_bookings
        ],
        "total": total,
        "skip": skip,
        "limit": limit,
        "subscription_tier": subscription_tier,
        "can_see_wider_area": can_see_wider_area
    }


# Consultations are managed by admin team, not individual providers
# Removed /me/consultations endpoint - use /admin/consultations instead


@router.get("/me/services")
async def get_my_services(
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current provider's services"""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    if current_user.role != UserRole.SERVICE_PROVIDER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Service provider role required."
        )
    
    provider = db.query(ServiceProvider).filter(ServiceProvider.user_id == current_user.id).first()
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider profile not found"
        )
    
    services = db.query(Service).filter(Service.provider_id == provider.id).all()
    
    return {
        "services": [
            {
                "id": s.id,
                "name": s.name,
                "category": s.category,
                "description": s.description,
                "base_price": float(s.base_price) if s.base_price else None,
                "is_active": s.is_active
            }
            for s in services
        ]
    }
