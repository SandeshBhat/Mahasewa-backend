"""Invoice management endpoints"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

from app.db.session import get_db
from app.models.user import User
from app.models.invoice import Invoice, InvoiceStatus, InvoiceType
from app.services.invoice_service import InvoiceService
from app.dependencies.auth import get_current_user, require_role

router = APIRouter()


@router.get("/")
async def list_my_invoices(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = None,
    invoice_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's invoices
    
    Returns list of invoices for the authenticated user
    """
    # Convert string status to enum if provided
    status_enum = None
    if status:
        try:
            status_enum = InvoiceStatus[status.upper()]
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status}. Valid values: {[s.value for s in InvoiceStatus]}"
            )
    
    # Convert string invoice_type to enum if provided
    type_enum = None
    if invoice_type:
        try:
            type_enum = InvoiceType[invoice_type.upper()]
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid invoice_type: {invoice_type}. Valid values: {[t.value for t in InvoiceType]}"
            )
    
    invoices = InvoiceService.get_user_invoices(
        db, current_user.id, status_enum, type_enum, skip, limit
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
                "customer_name": inv.customer_name,
                "base_amount": float(inv.base_amount),
                "gst_amount": float(inv.gst_amount),
                "total_amount": float(inv.total_amount),
                "status": inv.status.value,
                "payment_date": inv.payment_date.isoformat() if inv.payment_date else None,
                "payment_method": inv.payment_method,
                "created_at": inv.created_at.isoformat() if inv.created_at else None,
            }
            for inv in invoices
        ],
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/{invoice_id}")
async def get_invoice(
    invoice_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get invoice details
    
    Returns full details of a specific invoice
    """
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id,
        Invoice.user_id == current_user.id
    ).first()
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    return {
        "id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "invoice_type": invoice.invoice_type.value,
        "invoice_date": invoice.invoice_date.isoformat(),
        "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
        "customer_name": invoice.customer_name,
        "customer_email": invoice.customer_email,
        "customer_phone": invoice.customer_phone,
        "billing_name": invoice.billing_name,
        "billing_address": invoice.billing_address,
        "billing_gstin": invoice.billing_gstin,
        "base_amount": float(invoice.base_amount),
        "gst_rate": float(invoice.gst_rate),
        "gst_amount": float(invoice.gst_amount),
        "total_amount": float(invoice.total_amount),
        "status": invoice.status.value,
        "line_items": invoice.line_items,
        "payment_method": invoice.payment_method,
        "payment_reference": invoice.payment_reference,
        "payment_date": invoice.payment_date.isoformat() if invoice.payment_date else None,
        "notes": invoice.notes,
        "related_type": invoice.related_type,
        "related_id": invoice.related_id,
        "created_at": invoice.created_at.isoformat() if invoice.created_at else None,
        "updated_at": invoice.updated_at.isoformat() if invoice.updated_at else None,
    }


@router.get("/{invoice_id}/html")
async def get_invoice_html(
    invoice_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get invoice HTML representation
    
    Returns HTML content for invoice display/printing
    """
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id,
        Invoice.user_id == current_user.id
    ).first()
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    html_content = InvoiceService.get_invoice_html(invoice)
    
    return {
        "invoice_id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "html": html_content
    }


@router.get("/{invoice_id}/pdf")
async def get_invoice_pdf(
    invoice_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get invoice PDF (base64 encoded)
    
    Returns PDF content as base64 string
    """
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id,
        Invoice.user_id == current_user.id
    ).first()
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    # Generate PDF (currently returns HTML, but named for future PDF implementation)
    pdf_content = InvoiceService.generate_pdf(invoice)
    
    import base64
    pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
    
    return {
        "invoice_id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "pdf_base64": pdf_base64,
        "filename": f"Invoice_{invoice.invoice_number}.pdf"
    }


# Admin endpoints
@router.get("/admin/all", dependencies=[Depends(require_role(["admin", "super_admin"]))])
async def list_all_invoices(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = None,
    user_id: Optional[int] = None,
    invoice_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Admin: List all invoices
    
    Returns all invoices in the system with filtering
    """
    query = db.query(Invoice)
    
    # Filter by status
    if status:
        try:
            status_enum = InvoiceStatus[status.upper()]
            query = query.filter(Invoice.status == status_enum)
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status}"
            )
    
    # Filter by user_id
    if user_id:
        query = query.filter(Invoice.user_id == user_id)
    
    # Filter by invoice_type
    if invoice_type:
        try:
            type_enum = InvoiceType[invoice_type.upper()]
            query = query.filter(Invoice.invoice_type == type_enum)
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid invoice_type: {invoice_type}"
            )
    
    total = query.count()
    invoices = query.order_by(Invoice.invoice_date.desc())\
        .offset(skip).limit(limit).all()
    
    return {
        "invoices": [
            {
                "id": inv.id,
                "invoice_number": inv.invoice_number,
                "invoice_type": inv.invoice_type.value,
                "customer_name": inv.customer_name,
                "customer_email": inv.customer_email,
                "total_amount": float(inv.total_amount),
                "status": inv.status.value,
                "invoice_date": inv.invoice_date.isoformat(),
                "due_date": inv.due_date.isoformat() if inv.due_date else None,
                "payment_date": inv.payment_date.isoformat() if inv.payment_date else None,
                "user_id": inv.user_id,
            }
            for inv in invoices
        ],
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.post("/{invoice_id}/mark-paid", dependencies=[Depends(require_role(["admin", "super_admin"]))])
async def mark_invoice_paid(
    invoice_id: int,
    payment_method: str,
    payment_reference: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Admin: Mark invoice as paid
    
    Updates invoice status to PAID with payment details
    """
    try:
        invoice = InvoiceService.mark_as_paid(
            db=db,
            invoice_id=invoice_id,
            payment_method=payment_method,
            payment_reference=payment_reference
        )
        
        return {
            "message": "Invoice marked as paid",
            "invoice_id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "status": invoice.status.value,
            "payment_date": invoice.payment_date.isoformat() if invoice.payment_date else None,
            "payment_method": invoice.payment_method
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/stats/summary")
async def get_invoice_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get invoice statistics for current user
    
    Returns summary of pending, paid, and overdue invoices
    """
    from sqlalchemy import func
    from datetime import date
    
    # Total invoices
    total = db.query(func.count(Invoice.id))\
        .filter(Invoice.user_id == current_user.id)\
        .scalar()
    
    # Pending invoices
    pending = db.query(func.count(Invoice.id))\
        .filter(
            Invoice.user_id == current_user.id,
            Invoice.status == InvoiceStatus.PENDING
        ).scalar()
    
    # Paid invoices
    paid = db.query(func.count(Invoice.id))\
        .filter(
            Invoice.user_id == current_user.id,
            Invoice.status == InvoiceStatus.PAID
        ).scalar()
    
    # Overdue invoices (pending and past due date)
    overdue = db.query(func.count(Invoice.id))\
        .filter(
            Invoice.user_id == current_user.id,
            Invoice.status == InvoiceStatus.PENDING,
            Invoice.due_date < date.today()
        ).scalar()
    
    # Total amount pending
    pending_amount = db.query(func.sum(Invoice.total_amount))\
        .filter(
            Invoice.user_id == current_user.id,
            Invoice.status == InvoiceStatus.PENDING
        ).scalar() or 0
    
    # Total amount paid
    paid_amount = db.query(func.sum(Invoice.total_amount))\
        .filter(
            Invoice.user_id == current_user.id,
            Invoice.status == InvoiceStatus.PAID
        ).scalar() or 0
    
    return {
        "total_invoices": total or 0,
        "pending_count": pending or 0,
        "paid_count": paid or 0,
        "overdue_count": overdue or 0,
        "pending_amount": float(pending_amount),
        "paid_amount": float(paid_amount),
    }

