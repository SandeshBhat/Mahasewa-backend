"""Invoice generation service"""
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, Dict, List
from sqlalchemy.orm import Session
from io import BytesIO
import logging

from app.models.invoice import Invoice, InvoiceType, InvoiceStatus
from app.models.user import User

logger = logging.getLogger(__name__)

# Try to import WeasyPrint for PDF generation
try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False
    logger.warning("WeasyPrint not installed. PDF generation will use HTML fallback.")


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
        """Generate PDF for invoice using WeasyPrint"""
        
        # Format line items safely
        line_items_html = ""
        if invoice.line_items:
            for item in invoice.line_items:
                description = item.get('description', '')
                quantity = item.get('quantity', 1)
                rate = float(item.get('rate', 0))
                amount = float(item.get('amount', 0))
                line_items_html += f"<tr><td>{description}</td><td style='text-align: center;'>{quantity}</td><td style='text-align: right;'>{rate:.2f}</td><td style='text-align: right;'>{amount:.2f}</td></tr>"
        else:
            # Fallback if line_items is empty
            description = invoice.notes or "Service/Product"
            line_items_html = f"<tr><td>{description}</td><td style='text-align: center;'>1</td><td style='text-align: right;'>{float(invoice.base_amount):.2f}</td><td style='text-align: right;'>{float(invoice.base_amount):.2f}</td></tr>"
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        @page {{
            size: A4;
            margin: 2cm;
        }}
        body {{
            font-family: 'Arial', 'Helvetica', sans-serif;
            margin: 0;
            padding: 0;
            color: #333;
            line-height: 1.6;
        }}
        .header {{
            text-align: center;
            margin-bottom: 40px;
            padding-bottom: 20px;
            border-bottom: 3px solid #f97316;
        }}
        .header h1 {{
            color: #f97316;
            margin: 0;
            font-size: 2.5em;
        }}
        .header h2 {{
            color: #666;
            margin: 10px 0;
            font-size: 1.2em;
            font-weight: normal;
        }}
        .invoice-info {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 30px;
        }}
        .invoice-details {{
            flex: 1;
        }}
        .customer-details {{
            flex: 1;
            text-align: right;
        }}
        .invoice-details p, .customer-details p {{
            margin: 5px 0;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 30px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        th {{
            background-color: #f97316;
            color: white;
            font-weight: bold;
        }}
        tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        .totals {{
            margin-top: 30px;
            text-align: right;
        }}
        .totals p {{
            margin: 8px 0;
            font-size: 1.1em;
        }}
        .total-amount {{
            font-size: 1.5em;
            font-weight: bold;
            color: #f97316;
            border-top: 2px solid #f97316;
            padding-top: 10px;
            margin-top: 10px;
        }}
        .footer {{
            margin-top: 50px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            text-align: center;
            color: #666;
            font-size: 0.9em;
        }}
        .status-badge {{
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 0.9em;
        }}
        .status-paid {{
            background-color: #4CAF50;
            color: white;
        }}
        .status-pending {{
            background-color: #FF9800;
            color: white;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>INVOICE</h1>
        <h2>MahaSeWA - Maharashtra Societies Welfare Association</h2>
        <p>Email: info@mahasewa.org | Website: www.mahasewa.org</p>
    </div>
    
    <div class="invoice-info">
        <div class="invoice-details">
            <p><strong>Invoice Number:</strong> {invoice.invoice_number}</p>
            <p><strong>Invoice Date:</strong> {invoice.invoice_date.strftime('%d-%b-%Y')}</p>
            <p><strong>Due Date:</strong> {invoice.due_date.strftime('%d-%b-%Y') if invoice.due_date else 'N/A'}</p>
            <p><strong>Status:</strong> <span class="status-badge status-{invoice.status.value}">{invoice.status.value.upper()}</span></p>
        </div>
        
        <div class="customer-details">
            <h3 style="text-align: right; margin-top: 0;">Bill To:</h3>
            <p><strong>{invoice.customer_name}</strong></p>
            <p>{invoice.customer_email}</p>
            {f'<p>{invoice.customer_phone}</p>' if invoice.customer_phone else ''}
            {f'<p>{invoice.billing_address}</p>' if invoice.billing_address else ''}
            {f'<p><strong>GSTIN:</strong> {invoice.billing_gstin}</p>' if invoice.billing_gstin else ''}
        </div>
    </div>
    
    <table>
        <thead>
            <tr>
                <th>Description</th>
                <th style="text-align: center; width: 80px;">Quantity</th>
                <th style="text-align: right; width: 120px;">Rate (₹)</th>
                <th style="text-align: right; width: 120px;">Amount (₹)</th>
            </tr>
        </thead>
        <tbody>
            {line_items_html}
        </tbody>
    </table>
    
    <div class="totals">
        <p>Subtotal: ₹{float(invoice.base_amount):.2f}</p>
        <p>GST ({float(invoice.gst_rate)}%): ₹{float(invoice.gst_amount):.2f}</p>
        <p class="total-amount">Total Amount: ₹{float(invoice.total_amount):.2f}</p>
    </div>
    
    {f'<div style="margin-top: 30px;"><p><strong>Payment Method:</strong> {invoice.payment_method}</p><p><strong>Payment Date:</strong> {invoice.payment_date.strftime("%d-%b-%Y") if invoice.payment_date else "N/A"}</p></div>' if invoice.payment_method else ''}
    
    {f'<div style="margin-top: 20px;"><p><strong>Notes:</strong> {invoice.notes}</p></div>' if invoice.notes else ''}
    
    <div class="footer">
        <p><strong>Thank you for your business!</strong></p>
        <p>This is a computer-generated invoice. No signature required.</p>
        <p>For queries, contact: info@mahasewa.org</p>
    </div>
</body>
</html>
        """
        
        # Generate PDF using WeasyPrint if available
        if WEASYPRINT_AVAILABLE:
            try:
                # Create PDF from HTML
                pdf_bytes = HTML(string=html_content).write_pdf()
                return pdf_bytes
            except Exception as e:
                logger.error(f"Error generating PDF with WeasyPrint: {e}")
                # Fallback to HTML
                return html_content.encode('utf-8')
        else:
            # Fallback to HTML if WeasyPrint not available
            logger.warning("WeasyPrint not available, returning HTML instead of PDF")
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
