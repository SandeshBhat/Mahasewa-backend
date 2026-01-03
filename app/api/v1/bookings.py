"""Service booking endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel

from app.db.session import get_db
from app.models.booking import ServiceBooking, BookingStatus
from app.models.user import User
from app.models.provider import ServiceProvider, Service
from app.models.member import Member
from app.dependencies.auth import (
    get_current_user,
    get_current_member_user,
    get_current_admin_user,
    require_any_role
)
import uuid

router = APIRouter()


# ============ SCHEMAS ============

class BookingCreateRequest(BaseModel):
    """Request schema for creating a booking"""
    service_id: Optional[int] = None
    provider_id: int
    service_name: str  # Required in model
    requested_start_date: Optional[str] = None  # ISO format datetime
    description: Optional[str] = None
    requirements: Optional[dict] = None
    society_id: Optional[int] = None  # For society bookings
    client_notes: Optional[str] = None


class BookingUpdateRequest(BaseModel):
    """Request schema for updating a booking"""
    requested_start_date: Optional[str] = None
    description: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None


class BookingResponse(BaseModel):
    """Response schema for booking"""
    id: int
    service_id: int
    provider_id: int
    member_id: Optional[int]
    society_id: Optional[int]
    scheduled_date: str
    scheduled_time: Optional[str]
    location: Optional[str]
    status: str
    notes: Optional[str]
    service_name: Optional[str]
    provider_name: Optional[str]
    member_name: Optional[str]
    created_at: str


# ============ BOOKING ENDPOINTS ============

@router.post("/", response_model=dict)
async def create_booking(
    booking_data: BookingCreateRequest,
    current_user: User = Depends(require_any_role("mahasewa_member", "society_admin")),
    db: Session = Depends(get_db)
):
    """
    Create a new service booking with location-based matching
    
    Features:
    - Validates provider availability
    - Checks subscription-based area restrictions
    - Links to society if provided
    - Generates unique booking number
    
    Access: Members and Society Admins can create bookings
    """
    
    # Verify provider exists
    provider = db.query(ServiceProvider).filter(ServiceProvider.id == booking_data.provider_id).first()
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found"
        )
    
    # Verify service exists and belongs to provider
    service = None
    if booking_data.service_id:
        service = db.query(Service).filter(
            Service.id == booking_data.service_id,
            Service.provider_id == provider.id
        ).first()
        if not service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service not found or does not belong to provider"
            )
    
    # Check subscription-based area restrictions if society booking
    if booking_data.society_id:
        from app.models.society import Society
        from app.models.subscription import VendorSubscription, SubscriptionStatus
        from datetime import date
        import math
        
        society = db.query(Society).filter(Society.id == booking_data.society_id).first()
        if not society:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Society not found"
            )
        
        # Check if vendor can serve this society based on subscription
        active_subscription = db.query(VendorSubscription).filter(
            VendorSubscription.service_provider_id == provider.id,
            VendorSubscription.status == SubscriptionStatus.ACTIVE,
            VendorSubscription.end_date >= date.today()
        ).first()
        
        subscription_tier = active_subscription.plan.tier.value if active_subscription and active_subscription.plan else None
        
        # Check distance if both have coordinates
        if provider.latitude and provider.longitude and society.latitude and society.longitude:
            R = 6371  # Earth's radius in km
            lat1_rad = math.radians(float(provider.latitude))
            lat2_rad = math.radians(float(society.latitude))
            delta_lat = math.radians(float(society.latitude) - float(provider.latitude))
            delta_lon = math.radians(float(society.longitude) - float(provider.longitude))
            
            a = math.sin(delta_lat / 2) ** 2 + \
                math.cos(lat1_rad) * math.cos(lat2_rad) * \
                math.sin(delta_lon / 2) ** 2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            distance_km = R * c
            
            # Get max radius based on subscription
            max_radius_map = {
                'basic_monthly': 10,
                'basic_yearly': 10,
                'premium_monthly': 25,
                'premium_yearly': 25,
                'elite_yearly': 999999
            }
            max_radius = max_radius_map.get(subscription_tier, 10) if subscription_tier else 10
            
            if distance_km > max_radius:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Provider can only serve societies within {max_radius}km. Distance: {distance_km:.1f}km. Upgrade subscription to serve wider area."
                )
        elif provider.city and society.city:
            # Fallback to city matching if no coordinates
            if provider.city.lower() != society.city.lower():
                if not subscription_tier or subscription_tier in ['basic_monthly', 'basic_yearly']:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Provider can only serve societies in the same city. Upgrade subscription to serve wider area."
                    )
    
    # Generate unique booking number
    booking_number = f"BK-{uuid.uuid4().hex[:8].upper()}"
    
    # Parse requested_start_date if provided
    requested_start_date = None
    if booking_data.requested_start_date:
        try:
            requested_start_date = datetime.fromisoformat(booking_data.requested_start_date.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)"
            )
    
    # Create booking
    new_booking = ServiceBooking(
        booking_number=booking_number,
        client_user_id=current_user.id,
        provider_id=booking_data.provider_id,
        service_id=booking_data.service_id,
        society_id=booking_data.society_id,
        service_name=booking_data.service_name,
        description=booking_data.description,
        requirements=booking_data.requirements,
        requested_start_date=requested_start_date,
        status=BookingStatus.REQUESTED,
        client_notes=booking_data.client_notes
    )
    
    db.add(new_booking)
    db.commit()
    db.refresh(new_booking)
    
    # Send booking confirmation email
    try:
        from app.services.email_service import email_service
        email_service.send_booking_confirmation_email(
            user=current_user,
            booking_number=booking_number,
            service_name=booking_data.service_name or (service.name if service else "Service"),
            provider_name=provider.business_name
        )
    except Exception as e:
        # Log error but don't fail the request
        print(f"Error sending booking confirmation email: {e}")
    
    return {
        "success": True,
        "message": "Booking created successfully",
        "booking_id": new_booking.id,
        "booking": {
            "id": new_booking.id,
            "service_id": new_booking.service_id,
            "provider_id": new_booking.provider_id,
            "status": new_booking.status.value,
            "scheduled_date": new_booking.scheduled_date.isoformat() if new_booking.scheduled_date else None,
            "scheduled_time": new_booking.scheduled_time,
        }
    }


@router.get("/", response_model=dict)
async def list_bookings(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    status: Optional[str] = None,
    provider_id: Optional[int] = None,
    member_id: Optional[int] = None,
    society_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List bookings with role-based filtering:
    - Admins: See all bookings
    - Members: See only their bookings
    - Providers: See only their bookings
    - Society Admins: See bookings for their society
    """
    admin_roles = ["super_admin", "mahasewa_admin", "mahasewa_staff"]
    is_admin = current_user.role in admin_roles
    
    query = db.query(ServiceBooking)
    
    # Role-based filtering
    if not is_admin:
        if current_user.role == "mahasewa_member":
            # Members see only their bookings
            from app.models.member import Member
            member = db.query(Member).filter(Member.user_id == current_user.id).first()
            if member:
                query = query.filter(ServiceBooking.client_user_id == current_user.id)
            else:
                # No member profile, return empty
                return {"bookings": [], "total": 0, "skip": skip, "limit": limit}
        
        elif current_user.role == "service_provider":
            # Providers see only their bookings
            provider = db.query(ServiceProvider).filter(ServiceProvider.user_id == current_user.id).first()
            if provider:
                query = query.filter(ServiceBooking.provider_id == provider.id)
            else:
                return {"bookings": [], "total": 0, "skip": skip, "limit": limit}
        
        elif current_user.role == "society_admin":
            # Society admins see bookings for their society
            from app.models.society import Society
            society = db.query(Society).filter(Society.admin_user_id == current_user.id).first()
            if society:
                query = query.filter(ServiceBooking.society_id == society.id)
            else:
                return {"bookings": [], "total": 0, "skip": skip, "limit": limit}
        else:
            # Other roles can't access
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
    # Apply filters (only if admin or if explicitly provided)
    if status:
        try:
            status_enum = BookingStatus[status.upper()]
            query = query.filter(ServiceBooking.status == status_enum)
        except KeyError:
            pass
    
    if provider_id and is_admin:
        query = query.filter(ServiceBooking.provider_id == provider_id)
    
    if member_id and is_admin:
        query = query.filter(ServiceBooking.client_user_id == member_id)
    
    if society_id and is_admin:
        query = query.filter(ServiceBooking.society_id == society_id)
    
    total = query.count()
    bookings = query.order_by(ServiceBooking.created_at.desc()).offset(skip).limit(limit).all()
    
    return {
        "bookings": [
            {
                "id": b.id,
                "booking_number": b.booking_number,
                "service_id": b.service_id,
                "provider_id": b.provider_id,
                "client_user_id": b.client_user_id,
                "society_id": b.society_id,
                "service_name": b.service_name,
                "description": b.description,
                "requested_start_date": b.requested_start_date.isoformat() if b.requested_start_date else None,
                "status": b.status.value,
                "quote_amount": float(b.quote_amount) if b.quote_amount else None,
                "final_amount": float(b.final_amount) if b.final_amount else None,
                "payment_status": b.payment_status,
                "service_name_display": b.service.name if b.service else b.service_name,
                "provider_name": b.provider.business_name if b.provider else None,
                "client_name": b.client.full_name if b.client else None,
                "created_at": b.created_at.isoformat() if b.created_at else None,
            }
            for b in bookings
        ],
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/my", response_model=dict)
async def get_my_bookings(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    status: Optional[str] = None,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's bookings"""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Filter by current user's bookings
    query = db.query(ServiceBooking).filter(ServiceBooking.client_user_id == current_user.id)
    
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
                "service_name": b.service_name,
                "description": b.description,
                "requested_start_date": b.requested_start_date.isoformat() if b.requested_start_date else None,
                "status": b.status.value,
                "quote_amount": float(b.quote_amount) if b.quote_amount else None,
                "final_amount": float(b.final_amount) if b.final_amount else None,
                "payment_status": b.payment_status,
                "service_name_display": b.service.name if b.service else b.service_name,
                "provider_name": b.provider.business_name if b.provider else None,
                "created_at": b.created_at.isoformat() if b.created_at else None,
            }
            for b in bookings
        ],
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/{booking_id}", response_model=dict)
async def get_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Get booking details"""
    booking = db.query(ServiceBooking).filter(ServiceBooking.id == booking_id).first()
    
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    return {
        "id": booking.id,
        "booking_number": booking.booking_number,
        "service_id": booking.service_id,
        "provider_id": booking.provider_id,
        "client_user_id": booking.client_user_id,
        "society_id": booking.society_id,
        "service_name": booking.service_name,
        "description": booking.description,
        "requirements": booking.requirements,
        "requested_start_date": booking.requested_start_date.isoformat() if booking.requested_start_date else None,
        "expected_completion_date": booking.expected_completion_date.isoformat() if booking.expected_completion_date else None,
        "status": booking.status.value,
        "quote_amount": float(booking.quote_amount) if booking.quote_amount else None,
        "final_amount": float(booking.final_amount) if booking.final_amount else None,
        "payment_status": booking.payment_status,
        "client_notes": booking.client_notes,
        "provider_notes": booking.provider_notes,
        "service": {
            "id": booking.service.id if booking.service else None,
            "name": booking.service.name if booking.service else None,
            "description": booking.service.description if booking.service else None,
        } if booking.service else None,
        "provider": {
            "id": booking.provider.id if booking.provider else None,
            "business_name": booking.provider.business_name if booking.provider else None,
            "phone": booking.provider.phone if booking.provider else None,
            "email": booking.provider.email if booking.provider else None,
        } if booking.provider else None,
        "society": {
            "id": booking.society.id if booking.society else None,
            "name": booking.society.name if booking.society else None,
            "city": booking.society.city if booking.society else None,
            "address": booking.society.address if booking.society else None,
        } if booking.society else None,
        "client": {
            "id": booking.client.id if booking.client else None,
            "name": booking.client.full_name if booking.client else None,
            "email": booking.client.email if booking.client else None,
        } if booking.client else None,
        "created_at": booking.created_at.isoformat() if booking.created_at else None,
    }


@router.patch("/{booking_id}/status", response_model=dict)
async def update_booking_status(
    booking_id: int,
    new_status: str,
    notes: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Update booking status (provider or admin)"""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    booking = db.query(ServiceBooking).filter(ServiceBooking.id == booking_id).first()
    
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    # Check if user is provider or admin
    is_provider = False
    if current_user.role == "service_provider":
        provider = db.query(ServiceProvider).filter(ServiceProvider.user_id == current_user.id).first()
        if provider and booking.provider_id == provider.id:
            is_provider = True
    
    is_admin = current_user.role in ["admin", "super_admin", "mahasewa_admin"]
    
    if not (is_provider or is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only provider or admin can update booking status."
        )
    
    try:
        status_enum = BookingStatus[new_status.upper()]
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {', '.join([s.value for s in BookingStatus])}"
        )
    
    booking.status = status_enum
    
    if notes:
        booking.provider_notes = (booking.provider_notes or "") + f"\n[{datetime.utcnow().isoformat()}] {notes}"
    
    db.commit()
    db.refresh(booking)
    
    return {
        "success": True,
        "message": "Booking status updated",
        "booking": {
            "id": booking.id,
            "status": booking.status.value
        }
    }


@router.patch("/{booking_id}/accept", response_model=dict)
async def accept_booking(
    booking_id: int,
    notes: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Accept a booking (provider)"""
    return await update_booking_status(booking_id, "accepted", notes, db, current_user)


@router.patch("/{booking_id}/reject", response_model=dict)
async def reject_booking(
    booking_id: int,
    reason: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Reject a booking (provider)"""
    return await update_booking_status(booking_id, "cancelled", reason, db, current_user)


@router.put("/{booking_id}", response_model=dict)
async def update_booking(
    booking_id: int,
    booking_data: BookingUpdateRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Update booking details"""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    booking = db.query(ServiceBooking).filter(ServiceBooking.id == booking_id).first()
    
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    # Check if user is owner (client) or admin
    is_owner = booking.client_user_id == current_user.id
    
    is_admin = current_user.role in ["admin", "super_admin", "mahasewa_admin"]
    
    if not (is_owner or is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Update fields
    if booking_data.requested_start_date:
        try:
            booking.requested_start_date = datetime.fromisoformat(booking_data.requested_start_date.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format"
            )
    
    if booking_data.description is not None:
        booking.description = booking_data.description
    
    if booking_data.notes is not None:
        booking.client_notes = booking_data.notes
    
    if booking_data.status:
        try:
            status_enum = BookingStatus[booking_data.status.upper()]
            booking.status = status_enum
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid status"
            )
    
    db.commit()
    db.refresh(booking)
    
    return {
        "success": True,
        "message": "Booking updated successfully",
        "booking": {
            "id": booking.id,
            "requested_start_date": booking.requested_start_date.isoformat() if booking.requested_start_date else None,
            "status": booking.status.value
        }
    }


@router.post("/{booking_id}/create-payment", response_model=dict)
async def create_booking_payment(
    booking_id: int,
    payment_type: str = "full",  # "full" or "advance"
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create payment order for a booking
    
    Payment types:
    - "full": Pay full quote/final amount
    - "advance": Pay advance amount (typically 10-30% of quote)
    """
    from app.models.invoice import Invoice, InvoiceType, InvoiceStatus
    from app.services.invoice_service import InvoiceService
    from decimal import Decimal
    
    booking = db.query(ServiceBooking).filter(ServiceBooking.id == booking_id).first()
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    # Verify booking belongs to user
    if booking.client_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. This booking does not belong to you."
        )
    
    # Check if booking has a quote
    if not booking.quote_amount and not booking.final_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No quote available for this booking. Please wait for the provider to provide a quote."
        )
    
    # Determine payment amount
    amount_to_pay = None
    if payment_type == "full":
        amount_to_pay = booking.final_amount or booking.quote_amount
    elif payment_type == "advance":
        # Advance is typically 20% of quote
        quote = booking.final_amount or booking.quote_amount
        amount_to_pay = Decimal(str(quote)) * Decimal("0.20")
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payment_type. Must be 'full' or 'advance'"
        )
    
    if not amount_to_pay or amount_to_pay <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payment amount"
        )
    
    # Create invoice for booking
    try:
        invoice = InvoiceService.create_service_booking_invoice(
            db=db,
            user=current_user,
            booking_id=booking_id,
            amount=float(amount_to_pay),
            description=f"Service Booking Payment - {booking.service_name}",
            payment_type=payment_type
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create invoice: {str(e)}"
        )
    
    # Create Razorpay order
    try:
        from app.services.payment_service import payment_service
        
        if not payment_service.is_configured():
            raise HTTPException(
                status_code=503,
                detail="Payment gateway is not configured. Please contact administrator."
            )
        
        order = payment_service.create_order(
            amount=amount_to_pay,
            currency="INR",
            receipt=f"BK-{booking.booking_number}",
            notes={
                "booking_id": str(booking_id),
                "booking_number": booking.booking_number,
                "service_name": booking.service_name,
                "payment_type": payment_type,
                "user_id": str(current_user.id),
            },
            invoice_id=invoice.id
        )
        
        return {
            "success": True,
            "order_id": order.get("id"),
            "key_id": payment_service.get_key_id(),
            "amount": float(amount_to_pay),
            "currency": "INR",
            "invoice_id": invoice.id,
            "booking_id": booking_id,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create payment order: {str(e)}"
        )


@router.post("/{booking_id}/verify-payment", response_model=dict)
async def verify_booking_payment(
    booking_id: int,
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str,
    invoice_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Verify booking payment after Razorpay payment"""
    from app.models.invoice import Invoice, InvoiceStatus
    from app.services.payment_service import payment_service
    from app.schemas.payment import VerifyPaymentRequest
    
    booking = db.query(ServiceBooking).filter(ServiceBooking.id == booking_id).first()
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    # Verify booking belongs to user
    if booking.client_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Verify payment signature
    if not payment_service.is_configured():
        raise HTTPException(
            status_code=503,
            detail="Payment gateway is not configured"
        )
    
    try:
        is_valid = payment_service.verify_payment_signature(
            razorpay_order_id=razorpay_order_id,
            razorpay_payment_id=razorpay_payment_id,
            razorpay_signature=razorpay_signature
        )
        
        if not is_valid:
            raise HTTPException(status_code=400, detail="Invalid payment signature")
        
        # Get payment details from Razorpay
        payment_details = payment_service.get_payment_details(razorpay_payment_id)
        
        # Check payment status
        if payment_details.get("status") != "captured":
            raise HTTPException(
                status_code=400,
                detail=f"Payment not captured. Status: {payment_details.get('status')}"
            )
        
        # Update invoice
        invoice = db.query(Invoice).filter(
            Invoice.id == invoice_id,
            Invoice.user_id == current_user.id
        ).first()
        
        if invoice:
            payment_service.update_invoice_after_payment(
                invoice=invoice,
                razorpay_order_id=razorpay_order_id,
                razorpay_payment_id=razorpay_payment_id
            )
            db.commit()
            db.refresh(invoice)
            
            # Update booking payment status
            if invoice.status == InvoiceStatus.PAID:
                booking.payment_status = "paid"
                if invoice.total_amount:
                    booking.advance_paid = float(invoice.total_amount)
                db.commit()
            
            # Send payment confirmation email
            try:
                from app.services.email_service import email_service
                email_service.send_payment_confirmation_email(
                    user=current_user,
                    invoice_number=invoice.invoice_number,
                    amount=float(invoice.total_amount),
                    payment_id=razorpay_payment_id
                )
            except Exception as e:
                print(f"Error sending payment confirmation email: {e}")
        
        return {
            "success": True,
            "payment_id": razorpay_payment_id,
            "order_id": razorpay_order_id,
            "amount": float(payment_details.get("amount", 0)) / 100,
            "invoice_id": invoice.id if invoice else None,
            "booking_id": booking_id,
            "message": "Payment verified and booking updated successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Payment verification failed: {str(e)}")


@router.get("/stats/summary", response_model=dict)
async def get_booking_stats(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Get booking statistics"""
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
    
    total = db.query(ServiceBooking).count()
    requested = db.query(ServiceBooking).filter(ServiceBooking.status == BookingStatus.REQUESTED).count()
    accepted = db.query(ServiceBooking).filter(ServiceBooking.status == BookingStatus.ACCEPTED).count()
    in_progress = db.query(ServiceBooking).filter(ServiceBooking.status == BookingStatus.IN_PROGRESS).count()
    completed = db.query(ServiceBooking).filter(ServiceBooking.status == BookingStatus.COMPLETED).count()
    cancelled = db.query(ServiceBooking).filter(ServiceBooking.status == BookingStatus.CANCELLED).count()
    
    return {
        "total": total,
        "requested": requested,
        "accepted": accepted,
        "in_progress": in_progress,
        "completed": completed,
        "cancelled": cancelled
    }
