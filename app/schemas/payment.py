"""Payment schemas for request/response validation"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from decimal import Decimal


class CreatePaymentOrderRequest(BaseModel):
    """Request to create a payment order"""
    amount: Decimal = Field(..., gt=0, description="Amount in INR")
    currency: Optional[str] = Field("INR", description="Currency code")
    receipt: Optional[str] = Field(None, description="Receipt ID")
    invoice_id: Optional[int] = Field(None, description="Related invoice ID")
    purchase_id: Optional[int] = Field(None, description="Related purchase ID")
    notes: Optional[Dict[str, Any]] = Field(None, description="Additional notes")


class CreatePaymentOrderResponse(BaseModel):
    """Response after creating payment order"""
    order_id: str = Field(..., description="Razorpay order ID")
    amount: float = Field(..., description="Amount in INR")
    currency: str = Field(..., description="Currency code")
    key_id: str = Field(..., description="Razorpay key ID for frontend")
    receipt: Optional[str] = Field(None, description="Receipt ID")
    status: str = Field(..., description="Order status")


class VerifyPaymentRequest(BaseModel):
    """Request to verify payment"""
    razorpay_order_id: str = Field(..., description="Razorpay order ID")
    razorpay_payment_id: str = Field(..., description="Razorpay payment ID")
    razorpay_signature: str = Field(..., description="Payment signature")
    invoice_id: Optional[int] = Field(None, description="Related invoice ID")
    purchase_id: Optional[int] = Field(None, description="Related purchase ID")


class VerifyPaymentResponse(BaseModel):
    """Response after verifying payment"""
    success: bool = Field(..., description="Verification success status")
    payment_id: str = Field(..., description="Razorpay payment ID")
    order_id: str = Field(..., description="Razorpay order ID")
    amount: float = Field(..., description="Amount paid")
    invoice_id: Optional[int] = Field(None, description="Updated invoice ID")
    purchase_id: Optional[int] = Field(None, description="Updated purchase ID")
    message: str = Field(..., description="Response message")


class PaymentWebhookRequest(BaseModel):
    """Webhook payload from Razorpay"""
    event: str = Field(..., description="Event type")
    payload: Dict[str, Any] = Field(..., description="Event payload")

