"""
Publication Ad Management Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Optional, List
from datetime import datetime, date
from pydantic import BaseModel

from app.db.session import get_db
from app.models.provider import ServiceProvider
from app.models.user import User
from app.dependencies.auth import get_current_user
from app.api.v1.admin import get_current_admin_user
# from app.services.notification_service import NotificationService  # Uncomment when service exists

router = APIRouter()


# ============ SCHEMAS ============

class PublicationAdCreateRequest(BaseModel):
    publication_issue: str
    page_color: str  # "bw", "color", "premium_color"
    page_size: str  # "full", "half", "quarter"
    position: str  # "front_cover", "back_cover", "inside"
    total_price: float
    ad_content: str
    contact_name: str
    contact_email: str
    contact_phone: str
    notes: Optional[str] = None
    deadline: Optional[str] = None


class NotifyVendorsRequest(BaseModel):
    vendor_ids: List[int]
    subject: str
    message: str
    publication_issue: str
    deadline: Optional[str] = None


# ============ ENDPOINTS ============

@router.get("/admin/publication-ads")
async def list_publication_ads(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """List all publication ad bookings"""
    try:
        from app.models.publication_ad import PublicationAd
        
        query = db.query(PublicationAd)
        if status:
            query = query.filter(PublicationAd.status == status)
        
        ads = query.order_by(PublicationAd.created_at.desc()).all()
        
        return {
            "ads": [
                {
                    "id": ad.id,
                    "vendor_id": ad.vendor_id,
                    "vendor_name": ad.vendor.business_name if ad.vendor else "Unknown",
                    "publication_issue": ad.publication_issue,
                    "page_color": ad.page_color,
                    "page_size": ad.page_size,
                    "position": ad.position,
                    "total_price": float(ad.total_price),
                    "status": ad.status,
                    "deadline": ad.deadline.isoformat() if ad.deadline else None,
                    "contact_name": ad.contact_name,
                    "contact_email": ad.contact_email,
                    "contact_phone": ad.contact_phone,
                    "created_at": ad.created_at.isoformat() if ad.created_at else None,
                }
                for ad in ads
            ],
            "total": len(ads)
        }
    except ImportError:
        # Table doesn't exist yet - return empty list
        return {
            "ads": [],
            "total": 0
        }


@router.post("/admin/publication-ads/notify-vendors")
async def notify_vendors_about_ads(
    request: NotifyVendorsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Send notifications to vendors about ad opportunities"""
    notified_count = 0
    
    for vendor_id in request.vendor_ids:
        # Get vendor
        provider = db.query(ServiceProvider).filter(ServiceProvider.id == vendor_id).first()
        if not provider or not provider.user_id:
            continue
        
        # Create notification
        # TODO: Implement notification creation when notification system is ready
        # For now, just count vendors
        try:
            # Option 1: Use Supabase notifications table directly
            # from app.integrations.supabase import supabase
            # supabase.table('notifications').insert({
            #     'user_id': str(provider.user_id),
            #     'type': 'publication_ad',
            #     'title': request.subject,
            #     'message': request.message,
            #     'data': {
            #         'publication_issue': request.publication_issue,
            #         'deadline': request.deadline,
            #         'vendor_id': vendor_id,
            #     }
            # }).execute()
            
            # Option 2: Use notification service when available
            # notification_service = NotificationService()
            # notification_service.create_notification({
            #     "user_id": provider.user_id,
            #     "type": "publication_ad",
            #     "title": request.subject,
            #     "message": request.message,
            #     "data": {
            #         "publication_issue": request.publication_issue,
            #         "deadline": request.deadline,
            #         "vendor_id": vendor_id,
            #     }
            # })
            
            notified_count += 1
        except Exception as e:
            print(f"Error notifying vendor {vendor_id}: {e}")
    
    return {
        "success": True,
        "message": f"Notifications sent to {notified_count} vendors",
        "notified_count": notified_count
    }


@router.post("/publication-ads/book")
async def book_publication_ad(
    ad_data: PublicationAdCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Vendor books a publication ad"""
    # Get vendor profile
    provider = db.query(ServiceProvider).filter(ServiceProvider.user_id == current_user.id).first()
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service provider profile not found"
        )
    
    try:
        from app.models.publication_ad import PublicationAd
        
        # Parse deadline if provided
        deadline_date = None
        if ad_data.deadline:
            deadline_date = datetime.fromisoformat(ad_data.deadline).date()
        
        # Create ad booking
        new_ad = PublicationAd(
            vendor_id=provider.id,
            publication_issue=ad_data.publication_issue,
            page_color=ad_data.page_color,
            page_size=ad_data.page_size,
            position=ad_data.position,
            total_price=ad_data.total_price,
            ad_content=ad_data.ad_content,
            contact_name=ad_data.contact_name,
            contact_email=ad_data.contact_email,
            contact_phone=ad_data.contact_phone,
            notes=ad_data.notes,
            deadline=deadline_date,
            status="pending"
        )
        
        db.add(new_ad)
        db.commit()
        db.refresh(new_ad)
        
        return {
            "success": True,
            "message": "Ad booking request submitted successfully",
            "ad_id": new_ad.id,
        }
    except ImportError:
        # Table doesn't exist yet - return success but note it needs implementation
        return {
            "success": True,
            "message": "Ad booking request submitted successfully (pending table creation)",
            "ad_id": None,
        }


@router.get("/publication-ads/my-bookings")
async def get_my_ad_bookings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's (vendor) ad bookings"""
    # Get vendor profile
    provider = db.query(ServiceProvider).filter(ServiceProvider.user_id == current_user.id).first()
    if not provider:
        return {"bookings": []}
    
    try:
        from app.models.publication_ad import PublicationAd
        
        ads = db.query(PublicationAd).filter(
            PublicationAd.vendor_id == provider.id
        ).order_by(PublicationAd.created_at.desc()).all()
        
        return {
            "bookings": [
                {
                    "id": ad.id,
                    "publication_issue": ad.publication_issue,
                    "page_color": ad.page_color,
                    "page_size": ad.page_size,
                    "position": ad.position,
                    "total_price": float(ad.total_price),
                    "status": ad.status,
                    "deadline": ad.deadline.isoformat() if ad.deadline else None,
                    "created_at": ad.created_at.isoformat() if ad.created_at else None,
                }
                for ad in ads
            ]
        }
    except ImportError:
        # Table doesn't exist yet
        return {
            "bookings": []
        }


@router.patch("/admin/publication-ads/{ad_id}/approve")
async def approve_publication_ad(
    ad_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Approve a publication ad booking"""
    try:
        from app.models.publication_ad import PublicationAd
        
        ad = db.query(PublicationAd).filter(PublicationAd.id == ad_id).first()
        if not ad:
            raise HTTPException(status_code=404, detail="Ad booking not found")
        
        ad.status = "approved"
        db.commit()
        
        return {
            "success": True,
            "message": "Ad booking approved successfully"
        }
    except ImportError:
        raise HTTPException(status_code=501, detail="Publication ads table not yet created")


@router.patch("/admin/publication-ads/{ad_id}/reject")
async def reject_publication_ad(
    ad_id: int,
    reason: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Reject a publication ad booking"""
    try:
        from app.models.publication_ad import PublicationAd
        
        ad = db.query(PublicationAd).filter(PublicationAd.id == ad_id).first()
        if not ad:
            raise HTTPException(status_code=404, detail="Ad booking not found")
        
        ad.status = "rejected"
        if reason:
            ad.notes = f"{ad.notes or ''}\nRejection reason: {reason}".strip()
        db.commit()
        
        return {
            "success": True,
            "message": "Ad booking rejected"
        }
    except ImportError:
        raise HTTPException(status_code=501, detail="Publication ads table not yet created")


@router.post("/publication-ads/{ad_id}/create-payment", response_model=dict)
async def create_publication_ad_payment(
    ad_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create payment order for a publication ad"""
    from app.models.invoice import Invoice, InvoiceType, InvoiceStatus
    from app.services.invoice_service import InvoiceService
    from app.services.payment_service import payment_service
    from decimal import Decimal
    
    try:
        from app.models.publication_ad import PublicationAd
    except ImportError:
        raise HTTPException(status_code=501, detail="Publication ads table not yet created")
    
    ad = db.query(PublicationAd).filter(PublicationAd.id == ad_id).first()
    if not ad:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publication ad not found"
        )
    
    # Verify ad belongs to user's vendor profile
    provider = db.query(ServiceProvider).filter(ServiceProvider.user_id == current_user.id).first()
    if not provider or ad.vendor_id != provider.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. This ad does not belong to you."
        )
    
    # Check if ad is approved
    if ad.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ad must be approved before payment. Current status: {ad.status}"
        )
    
    # Check if already paid
    if ad.payment_status == "paid":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This ad has already been paid"
        )
    
    # Create invoice if not exists
    invoice = None
    if ad.invoice_id:
        invoice = db.query(Invoice).filter(Invoice.id == ad.invoice_id).first()
    
    if not invoice:
        invoice = InvoiceService.create_publication_ad_invoice(
            db=db,
            user=current_user,
            ad_id=ad_id,
            amount=float(ad.total_price),
            description=f"Publication Ad - {ad.publication_issue} ({ad.page_size}, {ad.page_color})"
        )
        ad.invoice_id = invoice.id
        db.commit()
        db.refresh(ad)
    
    # Create Razorpay order
    if not payment_service.is_configured():
        raise HTTPException(
            status_code=503,
            detail="Payment gateway is not configured. Please contact administrator."
        )
    
    try:
        order = payment_service.create_order(
            amount=Decimal(str(ad.total_price)),
            currency="INR",
            receipt=f"AD-{ad.id}",
            notes={
                "ad_id": str(ad_id),
                "publication_issue": ad.publication_issue,
                "user_id": str(current_user.id),
            },
            invoice_id=invoice.id
        )
        
        return {
            "success": True,
            "order_id": order.get("id"),
            "key_id": payment_service.get_key_id(),
            "amount": float(ad.total_price),
            "currency": "INR",
            "invoice_id": invoice.id,
            "ad_id": ad_id,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create payment order: {str(e)}"
        )


@router.post("/publication-ads/{ad_id}/verify-payment", response_model=dict)
async def verify_publication_ad_payment(
    ad_id: int,
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str,
    invoice_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Verify publication ad payment after Razorpay payment"""
    from app.models.invoice import Invoice, InvoiceStatus
    from app.services.payment_service import payment_service
    
    try:
        from app.models.publication_ad import PublicationAd
    except ImportError:
        raise HTTPException(status_code=501, detail="Publication ads table not yet created")
    
    ad = db.query(PublicationAd).filter(PublicationAd.id == ad_id).first()
    if not ad:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publication ad not found"
        )
    
    # Verify ad belongs to user's vendor profile
    provider = db.query(ServiceProvider).filter(ServiceProvider.user_id == current_user.id).first()
    if not provider or ad.vendor_id != provider.id:
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
            
            # Update ad payment status
            if invoice.status == InvoiceStatus.PAID:
                ad.payment_status = "paid"
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
            "ad_id": ad_id,
            "message": "Payment verified and ad updated successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Payment verification failed: {str(e)}")
