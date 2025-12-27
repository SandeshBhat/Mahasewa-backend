"""Payment service for Razorpay integration"""
import razorpay
import hmac
import hashlib
from typing import Optional, Dict, Any
from decimal import Decimal
from datetime import datetime

from app.config import settings
from app.models.invoice import Invoice, InvoiceStatus


class PaymentService:
    """Service for handling Razorpay payments"""
    
    def __init__(self):
        """Initialize Razorpay client"""
        if settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET:
            self.client = razorpay.Client(
                auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
            )
        else:
            self.client = None
    
    def is_configured(self) -> bool:
        """Check if Razorpay is configured"""
        return self.client is not None
    
    def create_order(
        self,
        amount: Decimal,
        currency: str = "INR",
        receipt: Optional[str] = None,
        notes: Optional[Dict[str, Any]] = None,
        invoice_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create a Razorpay order
        
        Args:
            amount: Amount in paise (multiply by 100)
            currency: Currency code (default: INR)
            receipt: Receipt ID (optional)
            notes: Additional notes (optional)
            invoice_id: Related invoice ID (optional)
        
        Returns:
            Order details from Razorpay
        """
        if not self.is_configured():
            raise ValueError("Razorpay is not configured. Please set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET")
        
        # Convert amount to paise (Razorpay uses smallest currency unit)
        amount_paise = int(float(amount) * 100)
        
        # Prepare order data
        order_data = {
            "amount": amount_paise,
            "currency": currency,
            "payment_capture": 1,  # Auto-capture payment
        }
        
        if receipt:
            order_data["receipt"] = receipt
        
        if notes:
            order_data["notes"] = notes
        elif invoice_id:
            order_data["notes"] = {"invoice_id": str(invoice_id)}
        
        # Create order
        order = self.client.order.create(data=order_data)
        
        return order
    
    def verify_payment_signature(
        self,
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str
    ) -> bool:
        """
        Verify Razorpay payment signature
        
        Args:
            razorpay_order_id: Order ID from Razorpay
            razorpay_payment_id: Payment ID from Razorpay
            razorpay_signature: Signature from Razorpay
        
        Returns:
            True if signature is valid, False otherwise
        """
        if not self.is_configured():
            return False
        
        # Create message
        message = f"{razorpay_order_id}|{razorpay_payment_id}"
        
        # Generate signature
        generated_signature = hmac.new(
            settings.RAZORPAY_KEY_SECRET.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures
        return hmac.compare_digest(generated_signature, razorpay_signature)
    
    def verify_webhook_signature(
        self,
        payload: str,
        signature: str
    ) -> bool:
        """
        Verify Razorpay webhook signature
        
        Args:
            payload: Webhook payload (string)
            signature: Webhook signature from headers
        
        Returns:
            True if signature is valid, False otherwise
        """
        if not self.is_configured():
            return False
        
        # Generate signature
        generated_signature = hmac.new(
            settings.RAZORPAY_KEY_SECRET.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures
        return hmac.compare_digest(generated_signature, signature)
    
    def get_payment_details(self, payment_id: str) -> Dict[str, Any]:
        """
        Get payment details from Razorpay
        
        Args:
            payment_id: Razorpay payment ID
        
        Returns:
            Payment details from Razorpay
        """
        if not self.is_configured():
            raise ValueError("Razorpay is not configured")
        
        return self.client.payment.fetch(payment_id)
    
    def refund_payment(
        self,
        payment_id: str,
        amount: Optional[Decimal] = None,
        notes: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a refund for a payment
        
        Args:
            payment_id: Razorpay payment ID
            amount: Refund amount (if None, full refund)
            notes: Refund notes
        
        Returns:
            Refund details from Razorpay
        """
        if not self.is_configured():
            raise ValueError("Razorpay is not configured")
        
        refund_data = {}
        
        if amount:
            # Convert to paise
            refund_data["amount"] = int(float(amount) * 100)
        
        if notes:
            refund_data["notes"] = notes
        
        return self.client.payment.refund(payment_id, refund_data)
    
    def update_invoice_after_payment(
        self,
        invoice: Invoice,
        razorpay_order_id: str,
        razorpay_payment_id: str,
        payment_method: str = "razorpay"
    ) -> Invoice:
        """
        Update invoice after successful payment
        
        Args:
            invoice: Invoice object to update
            razorpay_order_id: Razorpay order ID
            razorpay_payment_id: Razorpay payment ID
            payment_method: Payment method (default: razorpay)
        
        Returns:
            Updated invoice
        """
        invoice.status = InvoiceStatus.PAID
        invoice.payment_method = payment_method
        invoice.payment_reference = f"{razorpay_order_id}|{razorpay_payment_id}"
        invoice.payment_date = datetime.now().date()
        
        return invoice


# Create global instance
payment_service = PaymentService()

