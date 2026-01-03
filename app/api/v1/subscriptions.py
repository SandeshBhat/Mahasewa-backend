"""Vendor subscription management endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional

from app.db.session import get_db
from app.models.subscription import VendorSubscriptionPlan, VendorSubscription, SubscriptionTier, SubscriptionStatus
from app.models.provider import ServiceProvider
from app.models.invoice import InvoiceType
from app.services.invoice_service import InvoiceService

router = APIRouter()


@router.get("/plans")
async def list_subscription_plans(
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """List all vendor subscription plans"""
    query = db.query(VendorSubscriptionPlan)
    
    if active_only:
        query = query.filter(VendorSubscriptionPlan.is_active == True)
    
    plans = query.order_by(VendorSubscriptionPlan.display_order).all()
    
    return {
        "plans": [
            {
                "id": p.id,
                "tier": p.tier.value,
                "name": p.name,
                "description": p.description,
                "base_price": float(p.base_price),
                "gst_rate": float(p.gst_rate),
                "total_price": float(p.total_price),
                "duration_months": p.duration_months,
                "features": p.features,
                "is_recommended": p.is_recommended,
                "max_service_categories": p.max_service_categories,
                "max_service_areas": p.max_service_areas,
                "featured_listing": p.featured_listing,
                "priority_ranking": p.priority_ranking
            }
            for p in plans
        ]
    }


@router.post("/subscribe/{provider_id}")
async def subscribe_vendor(
    provider_id: int,
    plan_id: int,
    auto_renew: bool = False,
    db: Session = Depends(get_db)
):
    """Subscribe a vendor to a plan"""
    # Get provider
    provider = db.query(ServiceProvider).filter(ServiceProvider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    # Get plan
    plan = db.query(VendorSubscriptionPlan).filter(VendorSubscriptionPlan.id == plan_id).first()
    if not plan or not plan.is_active:
        raise HTTPException(status_code=404, detail="Plan not found or inactive")
    
    # Calculate dates
    start_date = date.today()
    end_date = start_date + timedelta(days=plan.duration_months * 30)
    
    # Create subscription
    subscription = VendorSubscription(
        service_provider_id=provider_id,
        plan_id=plan_id,
        start_date=start_date,
        end_date=end_date,
        status=SubscriptionStatus.PENDING_PAYMENT,
        auto_renew=auto_renew
    )
    db.add(subscription)
    db.flush()
    
    # Generate invoice
    invoice = InvoiceService.create_membership_invoice(
        db=db,
        user=provider.user,
        invoice_type=InvoiceType.SUBSCRIPTION,
        base_amount=plan.base_price,
        gst_rate=plan.gst_rate,
        description=f"Vendor Subscription - {plan.name}",
        related_type="subscription",
        related_id=subscription.id,
        billing_address=provider.address
    )
    
    subscription.invoice_id = invoice.id
    db.commit()
    
    return {
        "success": True,
        "message": f"Subscription created. Invoice #{invoice.invoice_number} generated.",
        "subscription_id": subscription.id,
        "invoice_id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "total_amount": float(invoice.total_amount),
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat()
    }


@router.get("/vendor/{provider_id}")
async def get_vendor_subscriptions(
    provider_id: int,
    active_only: bool = False,
    db: Session = Depends(get_db)
):
    """Get subscriptions for a vendor"""
    query = db.query(VendorSubscription).filter(
        VendorSubscription.service_provider_id == provider_id
    )
    
    if active_only:
        query = query.filter(VendorSubscription.status == SubscriptionStatus.ACTIVE)
    
    subscriptions = query.order_by(VendorSubscription.created_at.desc()).all()
    
    return {
        "subscriptions": [
            {
                "id": s.id,
                "plan_name": s.plan.name,
                "plan_tier": s.plan.tier.value,
                "start_date": s.start_date.isoformat(),
                "end_date": s.end_date.isoformat(),
                "status": s.status.value,
                "is_active": s.is_active,
                "days_remaining": s.days_remaining,
                "paid_amount": float(s.paid_amount) if s.paid_amount else None,
                "auto_renew": s.auto_renew,
                "invoice_id": s.invoice_id
            }
            for s in subscriptions
        ]
    }


@router.post("/activate/{subscription_id}")
async def activate_subscription(
    subscription_id: int,
    payment_method: str,
    payment_reference: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Activate subscription after payment (admin only)"""
    subscription = db.query(VendorSubscription).filter(
        VendorSubscription.id == subscription_id
    ).first()
    
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    # Update subscription
    subscription.status = SubscriptionStatus.ACTIVE
    subscription.payment_date = date.today()
    subscription.paid_amount = subscription.plan.total_price
    
    # Mark invoice as paid
    if subscription.invoice_id:
        InvoiceService.mark_as_paid(
            db=db,
            invoice_id=subscription.invoice_id,
            payment_method=payment_method,
            payment_reference=payment_reference
        )
    
    # Activate provider
    provider = subscription.service_provider
    provider.is_active = True
    
    db.commit()
    
    return {
        "success": True,
        "message": "Subscription activated successfully",
        "subscription_id": subscription.id,
        "provider_id": provider.id
    }


# Seed default plans (run once)
@router.post("/seed-plans")
async def seed_subscription_plans(db: Session = Depends(get_db)):
    """Seed default subscription plans"""
    plans = [
        {
            "tier": SubscriptionTier.BASIC_MONTHLY,
            "name": "Basic - Monthly",
            "description": "Perfect for individual service providers",
            "base_price": Decimal("5000.00"),
            "gst_rate": Decimal("18.00"),
            "total_price": Decimal("5900.00"),
            "duration_months": 1,
            "max_service_categories": 3,
            "max_service_areas": 5,
            "featured_listing": False,
            "priority_ranking": 1,
            "display_order": 1,
            "features": ["Basic Listing", "Contact Details", "Service Categories (3)", "Service Areas (5)"]
        },
        {
            "tier": SubscriptionTier.BASIC_YEARLY,
            "name": "Basic - Yearly",
            "description": "Save 2 months with annual payment",
            "base_price": Decimal("50000.00"),
            "gst_rate": Decimal("18.00"),
            "total_price": Decimal("59000.00"),
            "duration_months": 12,
            "max_service_categories": 5,
            "max_service_areas": 10,
            "featured_listing": False,
            "priority_ranking": 2,
            "display_order": 2,
            "is_recommended": True,
            "features": ["All Basic Features", "Service Categories (5)", "Service Areas (10)", "Save 2 months cost"]
        },
        {
            "tier": SubscriptionTier.PREMIUM_MONTHLY,
            "name": "Premium - Monthly",
            "description": "Enhanced visibility and features",
            "base_price": Decimal("15000.00"),
            "gst_rate": Decimal("18.00"),
            "total_price": Decimal("17700.00"),
            "duration_months": 1,
            "max_service_categories": 10,
            "max_service_areas": 20,
            "featured_listing": True,
            "priority_ranking": 5,
            "display_order": 3,
            "features": ["Featured Listing", "Unlimited Categories", "Unlimited Areas", "Priority Search", "Customer Reviews"]
        },
        {
            "tier": SubscriptionTier.PREMIUM_YEARLY,
            "name": "Premium - Yearly",
            "description": "Best value for growing businesses",
            "base_price": Decimal("150000.00"),
            "gst_rate": Decimal("18.00"),
            "total_price": Decimal("177000.00"),
            "duration_months": 12,
            "max_service_categories": 999,
            "max_service_areas": 999,
            "featured_listing": True,
            "priority_ranking": 6,
            "display_order": 4,
            "features": ["All Premium Features", "Save 3 months cost", "Priority Support", "Analytics Dashboard"]
        },
        {
            "tier": SubscriptionTier.ELITE_YEARLY,
            "name": "Elite - Yearly",
            "description": "Maximum exposure and premium benefits",
            "base_price": Decimal("500000.00"),
            "gst_rate": Decimal("18.00"),
            "total_price": Decimal("590000.00"),
            "duration_months": 12,
            "max_service_categories": 999,
            "max_service_areas": 999,
            "featured_listing": True,
            "priority_ranking": 10,
            "display_order": 5,
            "features": ["Top Search Ranking", "Featured on Homepage", "Dedicated Account Manager", "Custom Branding", "Exclusive Events Access", "Priority Support 24/7"]
        }
    ]
    
    created_count = 0
    for plan_data in plans:
        existing = db.query(VendorSubscriptionPlan).filter(
            VendorSubscriptionPlan.tier == plan_data["tier"]
        ).first()
        
        if not existing:
            plan = VendorSubscriptionPlan(**plan_data)
            db.add(plan)
            created_count += 1
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Created {created_count} subscription plans",
        "total_plans": len(plans)
    }
