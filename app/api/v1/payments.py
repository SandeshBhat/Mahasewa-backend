"""Payment API endpoints for Razorpay integration"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from typing import Optional
from decimal import Decimal
import json

from app.db.session import get_db
from app.models.user import User
from app.models.invoice import Invoice, InvoiceStatus
from app.models.content import PurchaseHistory
from app.dependencies.auth import get_current_user
from app.api.v1.admin import get_current_admin_user
from app.services.payment_service import payment_service
from app.services.invoice_service import InvoiceService
from app.schemas.payment import (
    CreatePaymentOrderRequest,
    CreatePaymentOrderResponse,
    VerifyPaymentRequest,
    VerifyPaymentResponse,
    PaymentWebhookRequest
)

router = APIRouter()


@router.post("/create-order", response_model=CreatePaymentOrderResponse)
async def create_payment_order(
    request: CreatePaymentOrderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a Razorpay payment order
    
    This endpoint creates a payment order in Razorpay and returns the order details
    needed to initiate the payment on the frontend.
    """
    if not payment_service.is_configured():
        raise HTTPException(
            status_code=503,
            detail="Payment gateway is not configured. Please contact administrator."
        )
    
    try:
        # Validate amount
        if request.amount <= 0:
            raise HTTPException(status_code=400, detail="Amount must be greater than 0")
        
        # Prepare notes
        notes = request.notes or {}
        notes["user_id"] = str(current_user.id)
        notes["user_email"] = current_user.email
        
        if request.invoice_id:
            notes["invoice_id"] = str(request.invoice_id)
            # Verify invoice belongs to user
            invoice = db.query(Invoice).filter(
                Invoice.id == request.invoice_id,
                Invoice.user_id == current_user.id
            ).first()
            
            if not invoice:
                raise HTTPException(status_code=404, detail="Invoice not found")
            
            if invoice.status == InvoiceStatus.PAID:
                raise HTTPException(status_code=400, detail="Invoice already paid")
            
            # Use invoice amount if not specified
            if not request.amount:
                request.amount = invoice.total_amount
        
        # Create Razorpay order
        order = payment_service.create_order(
            amount=Decimal(str(request.amount)),
            currency=request.currency or "INR",
            receipt=request.receipt,
            notes=notes,
            invoice_id=request.invoice_id
        )
        
        return CreatePaymentOrderResponse(
            order_id=order["id"],
            amount=float(order["amount"]) / 100,  # Convert from paise to rupees
            currency=order["currency"],
            key_id=payment_service.client.auth[0],  # Razorpay key ID
            receipt=order.get("receipt"),
            status=order.get("status", "created")
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create payment order: {str(e)}")


@router.post("/verify", response_model=VerifyPaymentResponse)
async def verify_payment(
    request: VerifyPaymentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Verify Razorpay payment signature and update invoice/purchase status
    
    This endpoint verifies the payment signature from Razorpay and updates
    the related invoice or purchase record.
    """
    if not payment_service.is_configured():
        raise HTTPException(
            status_code=503,
            detail="Payment gateway is not configured"
        )
    
    try:
        # Verify payment signature
        is_valid = payment_service.verify_payment_signature(
            razorpay_order_id=request.razorpay_order_id,
            razorpay_payment_id=request.razorpay_payment_id,
            razorpay_signature=request.razorpay_signature
        )
        
        if not is_valid:
            raise HTTPException(status_code=400, detail="Invalid payment signature")
        
        # Get payment details from Razorpay
        payment_details = payment_service.get_payment_details(request.razorpay_payment_id)
        
        # Check payment status
        if payment_details.get("status") != "captured":
            raise HTTPException(
                status_code=400,
                detail=f"Payment not captured. Status: {payment_details.get('status')}"
            )
        
        # Update invoice if invoice_id provided
        invoice = None
        if request.invoice_id:
            invoice = db.query(Invoice).filter(
                Invoice.id == request.invoice_id,
                Invoice.user_id == current_user.id
            ).first()
            
            if invoice:
                payment_service.update_invoice_after_payment(
                    invoice=invoice,
                    razorpay_order_id=request.razorpay_order_id,
                    razorpay_payment_id=request.razorpay_payment_id
                )
                db.commit()
                db.refresh(invoice)
                
                # Send payment confirmation email
                try:
                    from app.services.email_service import email_service
                    email_service.send_payment_confirmation_email(
                        user=current_user,
                        invoice_number=invoice.invoice_number,
                        amount=float(invoice.total_amount),
                        payment_id=request.razorpay_payment_id
                    )
                except Exception as e:
                    # Log error but don't fail the request
                    print(f"Error sending payment confirmation email: {e}")
        
        # Update purchase if purchase_id provided
        purchase = None
        if request.purchase_id:
            purchase = db.query(PurchaseHistory).filter(
                PurchaseHistory.id == request.purchase_id,
                PurchaseHistory.user_id == current_user.id
            ).first()
            
            if purchase:
                purchase.payment_status = "completed"
                purchase.payment_id = request.razorpay_payment_id
                purchase.payment_method = "razorpay"
                db.commit()
                db.refresh(purchase)
        
        return VerifyPaymentResponse(
            success=True,
            payment_id=request.razorpay_payment_id,
            order_id=request.razorpay_order_id,
            amount=float(payment_details.get("amount", 0)) / 100,
            invoice_id=invoice.id if invoice else None,
            purchase_id=purchase.id if purchase else None,
            message="Payment verified and processed successfully"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Payment verification failed: {str(e)}")


@router.post("/webhook")
async def payment_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Handle Razorpay webhook events
    
    This endpoint receives webhook events from Razorpay for payment status updates.
    It handles events like payment.captured, payment.failed, refund.created, etc.
    """
    if not payment_service.is_configured():
        raise HTTPException(
            status_code=503,
            detail="Payment gateway is not configured"
        )
    
    try:
        # Get webhook payload
        payload = await request.body()
        payload_str = payload.decode('utf-8')
        
        # Get signature from headers
        signature = request.headers.get("X-Razorpay-Signature")
        if not signature:
            raise HTTPException(status_code=400, detail="Missing webhook signature")
        
        # Verify webhook signature
        is_valid = payment_service.verify_webhook_signature(
            payload=payload_str,
            signature=signature
        )
        
        if not is_valid:
            raise HTTPException(status_code=400, detail="Invalid webhook signature")
        
        # Parse webhook event
        event_data = json.loads(payload_str)
        event_type = event_data.get("event")
        payment_data = event_data.get("payload", {}).get("payment", {})
        order_data = event_data.get("payload", {}).get("order", {})
        
        # Handle different event types
        if event_type == "payment.captured":
            payment_id = payment_data.get("id")
            order_id = order_data.get("id")
            amount = float(payment_data.get("amount", 0)) / 100
            
            # Get notes from order
            notes = order_data.get("notes", {})
            invoice_id = notes.get("invoice_id")
            purchase_id = notes.get("purchase_id")
            
            # Update invoice
            if invoice_id:
                invoice = db.query(Invoice).filter(Invoice.id == int(invoice_id)).first()
                if invoice and invoice.status != InvoiceStatus.PAID:
                    payment_service.update_invoice_after_payment(
                        invoice=invoice,
                        razorpay_order_id=order_id,
                        razorpay_payment_id=payment_id
                    )
                    db.commit()
            
            # Update purchase
            if purchase_id:
                purchase = db.query(PurchaseHistory).filter(
                    PurchaseHistory.id == int(purchase_id)
                ).first()
                if purchase and purchase.payment_status != "completed":
                    purchase.payment_status = "completed"
                    purchase.payment_id = payment_id
                    purchase.payment_method = "razorpay"
                    db.commit()
        
        elif event_type == "payment.failed":
            # Handle failed payment
            payment_id = payment_data.get("id")
            notes = order_data.get("notes", {})
            invoice_id = notes.get("invoice_id")
            
            if invoice_id:
                invoice = db.query(Invoice).filter(Invoice.id == int(invoice_id)).first()
                if invoice:
                    # Optionally update invoice status or create failed payment record
                    pass
        
        elif event_type == "refund.created":
            # Handle refund
            refund_data = event_data.get("payload", {}).get("refund", {})
            payment_id = refund_data.get("payment_id")
            # Update invoice status to refunded if needed
            invoice = db.query(Invoice).filter(
                Invoice.payment_reference.like(f"%{payment_id}%")
            ).first()
            if invoice:
                invoice.status = InvoiceStatus.REFUNDED
                db.commit()
        
        return {"status": "success", "message": "Webhook processed"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Webhook processing failed: {str(e)}")


@router.get("/status/{payment_id}")
async def get_payment_status(
    payment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get payment status from Razorpay
    
    This endpoint fetches the current status of a payment from Razorpay.
    """
    if not payment_service.is_configured():
        raise HTTPException(
            status_code=503,
            detail="Payment gateway is not configured"
        )
    
    try:
        payment_details = payment_service.get_payment_details(payment_id)
        
        return {
            "payment_id": payment_id,
            "status": payment_details.get("status"),
            "amount": float(payment_details.get("amount", 0)) / 100,
            "currency": payment_details.get("currency"),
            "method": payment_details.get("method"),
            "created_at": payment_details.get("created_at")
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch payment status: {str(e)}")

