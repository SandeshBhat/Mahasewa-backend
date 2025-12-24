"""Invoice generation service"""
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, Dict, List
from sqlalchemy.orm import Session
from io import BytesIO

from app.models.invoice import Invoice, InvoiceType, InvoiceStatus
from app.models.user import User


class InvoiceService:
    """Service for invoice generation and management"""
    
    @staticmethod
    def generate_invoice_number(db: Session) -> str:
        """Generate sequential invoice number"""
        # Format: INV-YYYY-XXXXX (e.g., INV-2024-00001)
        current_year = datetime.now().year
        prefix = f"INV-{current_year}-"
        
        # Get last invoice of current year
        last_invoice = db.query(Invoice)\
            .filter(Invoice.invoice_number.like(f"{prefix}%"))\
            .order_by(Invoice.id.desc())\
            .first()
        
        if last_invoice:
            # Extract number and increment
            last_number = int(last_invoice.invoice_number.split('-')[-1])
            new_number = last_number + 1
        else:
            new_number = 1
        
        return f"{prefix}{new_number:05d}"
    
    @staticmethod
    def create_membership_invoice(
        db: Session,
        user: User,
        invoice_type: InvoiceType,
        base_amount: Decimal,
        gst_rate: Decimal = Decimal("18.00"),
        description: str = "Membership Fee",
        related_type: Optional[str] = None,
        related_id: Optional[int] = None,
        billing_address: Optional[str] = None,
        billing_gstin: Optional[str] = None
    ) -> Invoice:
        """Create an invoice for membership/subscription"""
        
        # Calculate GST
        gst_amount = (base_amount * gst_rate) / Decimal("100")
        total_amount = base_amount + gst_amount
        
        # Generate invoice number
        invoice_number = InvoiceService.generate_invoice_number(db)
        
        # Create line items
        line_items = [
            {
                "description": description,
                "quantity": 1,
                "rate": float(base_amount),
                "amount": float(base_amount)
            },
            {
                "description": f"GST ({gst_rate}%)",
                "quantity": 1,
                "rate": float(gst_amount),
                "amount": float(gst_amount)
            }
        ]
        
        # Create invoice
        invoice = Invoice(
            invoice_number=invoice_number,
            invoice_type=invoice_type,
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=7),
            user_id=user.id,
            customer_name=user.full_name,
            customer_email=user.email,
            customer_phone=user.phone,
            billing_name=user.full_name,
            billing_address=billing_address,
            billing_gstin=billing_gstin,
            base_amount=base_amount,
            gst_rate=gst_rate,
            gst_amount=gst_amount,
            total_amount=total_amount,
            line_items=line_items,
            status=InvoiceStatus.PENDING,
            related_type=related_type,
            related_id=related_id
        )
        
        db.add(invoice)
        db.commit()
        db.refresh(invoice)
        
        return invoice
    
    @staticmethod
    def generate_pdf(invoice: Invoice) -> bytes:
        """Generate PDF for invoice (simplified version)"""
        # TODO: Implement actual PDF generation with reportlab or weasyprint
        # For now, return a simple HTML-based PDF
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .header {{ text-align: center; margin-bottom: 30px; }}
        .invoice-details {{ margin-bottom: 20px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
        .total {{ text-align: right; font-weight: bold; font-size: 1.2em; }}
        .footer {{ margin-top: 40px; text-align: center; color: #666; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>INVOICE</h1>
        <h2>MahaSeWA - Maharashtra Societies Welfare Association</h2>
        <p>Email: info@mahasewa.org | Phone: +91-XXXXXXXXXX</p>
    </div>
    
    <div class="invoice-details">
        <p><strong>Invoice Number:</strong> {invoice.invoice_number}</p>
        <p><strong>Invoice Date:</strong> {invoice.invoice_date.strftime('%d-%b-%Y')}</p>
        <p><strong>Due Date:</strong> {invoice.due_date.strftime('%d-%b-%Y') if invoice.due_date else 'N/A'}</p>
    </div>
    
    <div class="customer-details">
        <h3>Bill To:</h3>
        <p><strong>{invoice.customer_name}</strong></p>
        <p>{invoice.customer_email}</p>
        <p>{invoice.customer_phone or ''}</p>
        {f'<p>{invoice.billing_address}</p>' if invoice.billing_address else ''}
        {f'<p>GSTIN: {invoice.billing_gstin}</p>' if invoice.billing_gstin else ''}
    </div>
    
    <table>
        <thead>
            <tr>
                <th>Description</th>
                <th>Quantity</th>
                <th>Rate (₹)</th>
                <th>Amount (₹)</th>
            </tr>
        </thead>
        <tbody>
            {''.join([
                f"<tr><td>{item['description']}</td><td>{item['quantity']}</td><td>{item['rate']:.2f}</td><td>{item['amount']:.2f}</td></tr>"
                for item in invoice.line_items
            ])}
        </tbody>
    </table>
    
    <div class="total">
        <p>Base Amount: ₹{float(invoice.base_amount):.2f}</p>
        <p>GST ({float(invoice.gst_rate)}%): ₹{float(invoice.gst_amount):.2f}</p>
        <p style="font-size: 1.3em; color: #4CAF50;">Total Amount: ₹{float(invoice.total_amount):.2f}</p>
    </div>
    
    <div class="footer">
        <p>Thank you for your business!</p>
        <p>This is a computer-generated invoice.</p>
    </div>
</body>
</html>
        """
        
        # For now, return HTML as bytes
        # In production, use weasyprint or reportlab to convert HTML to PDF
        return html_content.encode('utf-8')
    
    @staticmethod
    def get_invoice_html(invoice: Invoice) -> str:
        """Get HTML representation of invoice"""
        # Same as generate_pdf but returns string
        return InvoiceService.generate_pdf(invoice).decode('utf-8')
    
    @staticmethod
    def mark_as_paid(
        db: Session,
        invoice_id: int,
        payment_method: str,
        payment_reference: Optional[str] = None,
        payment_date: Optional[date] = None
    ) -> Invoice:
        """Mark invoice as paid"""
        invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            raise ValueError(f"Invoice {invoice_id} not found")
        
        invoice.status = InvoiceStatus.PAID
        invoice.payment_method = payment_method
        invoice.payment_reference = payment_reference
        invoice.payment_date = payment_date or date.today()
        
        db.commit()
        db.refresh(invoice)
        
        return invoice
    
    @staticmethod
    def get_user_invoices(
        db: Session,
        user_id: int,
        status: Optional[InvoiceStatus] = None,
        invoice_type: Optional[InvoiceType] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Invoice]:
        """Get invoices for a user"""
        query = db.query(Invoice).filter(Invoice.user_id == user_id)
        
        if status:
            query = query.filter(Invoice.status == status)
        
        if invoice_type:
            query = query.filter(Invoice.invoice_type == invoice_type)
        
        return query.order_by(Invoice.invoice_date.desc())\
            .offset(skip)\
            .limit(limit)\
            .all()
