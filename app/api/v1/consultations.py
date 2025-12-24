"""Consultation endpoints for admin management"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

from app.db.session import get_db
from app.models.consultation import Consultation, ConsultationStatus, ConsultationType
from app.models.user import User
from app.models.provider import ServiceProvider
from app.dependencies.auth import get_current_user

router = APIRouter()


@router.get("/")
async def list_consultations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    status: Optional[str] = None,
    provider_id: Optional[int] = None,
    client_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """List all consultations (admin only)"""
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
    
    query = db.query(Consultation)
    
    if status:
        try:
            status_enum = ConsultationStatus[status.upper()]
            query = query.filter(Consultation.status == status_enum)
        except KeyError:
            pass
    
    if provider_id:
        query = query.filter(Consultation.provider_id == provider_id)
    
    if client_id:
        query = query.filter(Consultation.client_user_id == client_id)
    
    total = query.count()
    consultations = query.order_by(Consultation.created_at.desc()).offset(skip).limit(limit).all()
    
    return {
        "consultations": [
            {
                "id": c.id,
                "client_user_id": c.client_user_id,
                "provider_id": c.provider_id,
                "consultation_type": c.consultation_type.value,
                "status": c.status.value,
                "scheduled_datetime": c.scheduled_datetime.isoformat() if c.scheduled_datetime else None,
                "duration_minutes": c.duration_minutes,
                "subject": c.subject,
                "description": c.description,
                "fee": float(c.fee) if c.fee else 0,
                "payment_status": c.payment_status,
                "client_name": c.client.full_name if c.client else None,
                "client_email": c.client.email if c.client else None,
                "provider_name": c.provider.business_name if c.provider else None,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in consultations
        ],
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/stats")
async def get_consultation_stats(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Get consultation statistics (admin only)"""
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
    
    total = db.query(Consultation).count()
    pending = db.query(Consultation).filter(Consultation.status == ConsultationStatus.PENDING).count()
    confirmed = db.query(Consultation).filter(Consultation.status == ConsultationStatus.CONFIRMED).count()
    completed = db.query(Consultation).filter(Consultation.status == ConsultationStatus.COMPLETED).count()
    cancelled = db.query(Consultation).filter(Consultation.status == ConsultationStatus.CANCELLED).count()
    
    return {
        "total": total,
        "pending": pending,
        "confirmed": confirmed,
        "completed": completed,
        "cancelled": cancelled
    }


@router.get("/{consultation_id}")
async def get_consultation(
    consultation_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Get consultation details (admin only)"""
    from sqlalchemy.orm import joinedload
    
    # Use eager loading to prevent N+1 queries
    consultation = db.query(Consultation).options(
        joinedload(Consultation.client),
        joinedload(Consultation.provider)
    ).filter(Consultation.id == consultation_id).first()
    
    if not consultation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consultation not found"
        )
    
    return {
        "id": consultation.id,
        "client_user_id": consultation.client_user_id,
        "provider_id": consultation.provider_id,
        "consultation_type": consultation.consultation_type.value,
        "status": consultation.status.value,
        "scheduled_datetime": consultation.scheduled_datetime.isoformat() if consultation.scheduled_datetime else None,
        "duration_minutes": consultation.duration_minutes,
        "meeting_url": consultation.meeting_url,
        "meeting_id": consultation.meeting_id,
        "venue": consultation.venue,
        "venue_address": consultation.venue_address,
        "subject": consultation.subject,
        "description": consultation.description,
        "fee": float(consultation.fee) if consultation.fee else 0,
        "payment_status": consultation.payment_status,
        "client_notes": consultation.client_notes,
        "provider_notes": consultation.provider_notes,
        "client_rating": consultation.client_rating,
        "client_feedback": consultation.client_feedback,
        "client": {
            "id": consultation.client.id if consultation.client else None,
            "name": consultation.client.full_name if consultation.client else None,
            "email": consultation.client.email if consultation.client else None,
            "phone": consultation.client.phone if consultation.client else None,
        } if consultation.client else None,
        "provider": {
            "id": consultation.provider.id if consultation.provider else None,
            "business_name": consultation.provider.business_name if consultation.provider else None,
            "email": consultation.provider.email if consultation.provider else None,
            "phone": consultation.provider.phone if consultation.provider else None,
        } if consultation.provider else None,
        "created_at": consultation.created_at.isoformat() if consultation.created_at else None,
    }


@router.patch("/{consultation_id}/status")
async def update_consultation_status(
    consultation_id: int,
    status: str,
    notes: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Update consultation status (admin only)"""
    consultation = db.query(Consultation).filter(Consultation.id == consultation_id).first()
    
    if not consultation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consultation not found"
        )
    
    try:
        new_status = ConsultationStatus[status.upper()]
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {', '.join([s.value for s in ConsultationStatus])}"
        )
    
    consultation.status = new_status
    
    if notes:
        consultation.provider_notes = notes
    
    db.commit()
    db.refresh(consultation)
    
    return {
        "success": True,
        "message": "Consultation status updated",
        "consultation": {
            "id": consultation.id,
            "status": consultation.status.value
        }
    }


@router.patch("/{consultation_id}/assign")
async def assign_consultation(
    consultation_id: int,
    provider_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Assign consultation to a provider (admin only)"""
    consultation = db.query(Consultation).filter(Consultation.id == consultation_id).first()
    
    if not consultation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consultation not found"
        )
    
    provider = db.query(ServiceProvider).filter(ServiceProvider.id == provider_id).first()
    
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found"
        )
    
    consultation.provider_id = provider_id
    db.commit()
    db.refresh(consultation)
    
    return {
        "success": True,
        "message": "Consultation assigned to provider",
        "consultation": {
            "id": consultation.id,
            "provider_id": consultation.provider_id,
            "provider_name": provider.business_name
        }
    }
