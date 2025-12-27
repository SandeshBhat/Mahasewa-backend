"""Compliance management endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date, datetime
from pydantic import BaseModel

from app.db.session import get_db
from app.models.compliance import (
    ComplianceRequirement, 
    ComplianceSubmission, 
    ComplianceCategory,
    ComplianceFrequency,
    SubmissionStatus
)
from app.models.society import Society
from app.models.user import User
from app.dependencies.auth import get_current_user
from app.api.v1.admin import get_current_admin_user

router = APIRouter()


# ============ SCHEMAS ============

class ComplianceRequirementCreate(BaseModel):
    """Request schema for creating a compliance requirement"""
    name: str
    description: Optional[str] = None
    category: str  # ComplianceCategory enum
    frequency: str  # ComplianceFrequency enum
    is_mandatory: bool = True
    applicable_to: Optional[List[str]] = None  # JSON array: ["all", "specific_states", etc.]
    required_documents: Optional[List[str]] = None  # JSON array
    checklist: Optional[List[str]] = None  # JSON array
    legal_reference: Optional[str] = None
    reference_url: Optional[str] = None
    is_active: bool = True


class ComplianceRequirementUpdate(BaseModel):
    """Request schema for updating a compliance requirement"""
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    frequency: Optional[str] = None
    is_mandatory: Optional[bool] = None
    applicable_to: Optional[List[str]] = None
    required_documents: Optional[List[str]] = None
    checklist: Optional[List[str]] = None
    legal_reference: Optional[str] = None
    reference_url: Optional[str] = None
    is_active: Optional[bool] = None


class ComplianceSubmissionCreate(BaseModel):
    """Request schema for creating a compliance submission"""
    requirement_id: int
    applicable_period: str  # "FY 2023-24", "Q1 2024", etc.
    due_date: str  # YYYY-MM-DD
    submitted_documents: Optional[List[str]] = None  # Array of document URLs
    notes: Optional[str] = None


class ComplianceSubmissionUpdate(BaseModel):
    """Request schema for updating a compliance submission"""
    applicable_period: Optional[str] = None
    due_date: Optional[str] = None
    submitted_documents: Optional[List[str]] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    verification_notes: Optional[str] = None


# ============ COMPLIANCE REQUIREMENTS (Admin Only) ============

@router.get("/requirements")
async def list_requirements(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    category: Optional[str] = None,
    frequency: Optional[str] = None,
    applicable_to: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """List compliance requirements"""
    query = db.query(ComplianceRequirement)
    
    # Apply filters
    if category:
        try:
            req_category = ComplianceCategory(category)
            query = query.filter(ComplianceRequirement.category == req_category)
        except ValueError:
            pass
    
    if frequency:
        try:
            req_frequency = ComplianceFrequency(frequency)
            query = query.filter(ComplianceRequirement.frequency == req_frequency)
        except ValueError:
            pass
    
    if applicable_to:
        query = query.filter(ComplianceRequirement.applicable_to == applicable_to)
    
    if is_active is not None:
        query = query.filter(ComplianceRequirement.is_active == is_active)
    
    total = query.count()
    requirements = query.order_by(ComplianceRequirement.created_at.desc()).offset(skip).limit(limit).all()
    
    return {
        "requirements": [
            {
                "id": req.id,
                "name": req.name,
                "description": req.description,
                "category": req.category.value,
                "frequency": req.frequency.value,
                "is_mandatory": req.is_mandatory,
                "applicable_to": req.applicable_to or [],
                "required_documents": req.required_documents or [],
                "checklist": req.checklist or [],
                "legal_reference": req.legal_reference,
                "reference_url": req.reference_url,
                "is_active": req.is_active,
                "created_at": req.created_at.isoformat() if req.created_at else None,
            }
            for req in requirements
        ],
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/requirements/{requirement_id}")
async def get_requirement(
    requirement_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Get a specific compliance requirement"""
    requirement = db.query(ComplianceRequirement).filter(ComplianceRequirement.id == requirement_id).first()
    
    if not requirement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Requirement not found"
        )
    
    return {
        "id": requirement.id,
        "name": requirement.name,
        "description": requirement.description,
        "category": requirement.category.value,
        "frequency": requirement.frequency.value,
        "is_mandatory": requirement.is_mandatory,
        "applicable_to": requirement.applicable_to or [],
        "required_documents": requirement.required_documents or [],
        "checklist": requirement.checklist or [],
        "legal_reference": requirement.legal_reference,
        "reference_url": requirement.reference_url,
        "is_active": requirement.is_active,
        "created_at": requirement.created_at.isoformat() if requirement.created_at else None,
    }


@router.post("/requirements")
async def create_requirement(
    requirement_data: ComplianceRequirementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Create a new compliance requirement (admin only)"""
    # Validate category and frequency
    try:
        category = ComplianceCategory(requirement_data.category)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid category. Valid categories: {[e.value for e in ComplianceCategory]}"
        )
    
    try:
        frequency = ComplianceFrequency(requirement_data.frequency)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid frequency. Valid frequencies: {[e.value for e in ComplianceFrequency]}"
        )
    
    new_requirement = ComplianceRequirement(
        name=requirement_data.name,
        description=requirement_data.description,
        category=category,
        frequency=frequency,
        is_mandatory=requirement_data.is_mandatory,
        applicable_to=requirement_data.applicable_to,
        required_documents=requirement_data.required_documents,
        checklist=requirement_data.checklist,
        legal_reference=requirement_data.legal_reference,
        reference_url=requirement_data.reference_url,
        is_active=requirement_data.is_active
    )
    
    db.add(new_requirement)
    db.commit()
    db.refresh(new_requirement)
    
    return {
        "success": True,
        "message": "Compliance requirement created successfully",
        "requirement": {
            "id": new_requirement.id,
            "name": new_requirement.name,
            "category": new_requirement.category.value,
        }
    }


@router.put("/requirements/{requirement_id}")
async def update_requirement(
    requirement_id: int,
    requirement_data: ComplianceRequirementUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Update a compliance requirement (admin only)"""
    requirement = db.query(ComplianceRequirement).filter(ComplianceRequirement.id == requirement_id).first()
    
    if not requirement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Requirement not found"
        )
    
    # Update fields
    if requirement_data.name is not None:
        requirement.name = requirement_data.name
    if requirement_data.description is not None:
        requirement.description = requirement_data.description
    if requirement_data.category is not None:
        try:
            requirement.category = ComplianceCategory(requirement_data.category)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid category. Valid categories: {[e.value for e in ComplianceCategory]}"
            )
    if requirement_data.frequency is not None:
        try:
            requirement.frequency = ComplianceFrequency(requirement_data.frequency)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid frequency. Valid frequencies: {[e.value for e in ComplianceFrequency]}"
            )
    if requirement_data.is_mandatory is not None:
        requirement.is_mandatory = requirement_data.is_mandatory
    if requirement_data.applicable_to is not None:
        requirement.applicable_to = requirement_data.applicable_to
    if requirement_data.required_documents is not None:
        requirement.required_documents = requirement_data.required_documents
    if requirement_data.checklist is not None:
        requirement.checklist = requirement_data.checklist
    if requirement_data.legal_reference is not None:
        requirement.legal_reference = requirement_data.legal_reference
    if requirement_data.reference_url is not None:
        requirement.reference_url = requirement_data.reference_url
    if requirement_data.is_active is not None:
        requirement.is_active = requirement_data.is_active
    
    db.commit()
    db.refresh(requirement)
    
    return {
        "success": True,
        "message": "Compliance requirement updated successfully",
        "requirement": {
            "id": requirement.id,
            "name": requirement.name,
        }
    }


@router.delete("/requirements/{requirement_id}")
async def delete_requirement(
    requirement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Delete a compliance requirement (admin only)"""
    requirement = db.query(ComplianceRequirement).filter(ComplianceRequirement.id == requirement_id).first()
    
    if not requirement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Requirement not found"
        )
    
    db.delete(requirement)
    db.commit()
    
    return {
        "success": True,
        "message": "Compliance requirement deleted successfully"
    }


# ============ COMPLIANCE SUBMISSIONS ============

@router.get("/submissions")
async def list_submissions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    society_id: Optional[int] = None,
    requirement_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """List compliance submissions"""
    query = db.query(ComplianceSubmission)
    
    # Apply filters
    if society_id:
        query = query.filter(ComplianceSubmission.society_id == society_id)
    
    if requirement_id:
        query = query.filter(ComplianceSubmission.requirement_id == requirement_id)
    
    if status:
        try:
            sub_status = SubmissionStatus(status)
            query = query.filter(ComplianceSubmission.status == sub_status)
        except ValueError:
            pass
    
    # If user is society admin, only show their society's submissions
    if current_user and current_user.role == "society_admin":
        society = db.query(Society).filter(Society.admin_user_id == current_user.id).first()
        if society:
            query = query.filter(ComplianceSubmission.society_id == society.id)
    
    total = query.count()
    submissions = query.order_by(ComplianceSubmission.created_at.desc()).offset(skip).limit(limit).all()
    
    return {
        "submissions": [
            {
                "id": sub.id,
                "society_id": sub.society_id,
                "requirement_id": sub.requirement_id,
                "requirement_name": sub.requirement.name if sub.requirement else None,
                "applicable_period": sub.applicable_period,
                "due_date": sub.due_date.isoformat() if sub.due_date else None,
                "submission_date": sub.submission_date.isoformat() if sub.submission_date else None,
                "status": sub.status.value,
                "submitted_documents": sub.submitted_documents or [],
                "verification_notes": sub.verification_notes,
                "created_at": sub.created_at.isoformat() if sub.created_at else None,
            }
            for sub in submissions
        ],
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/submissions/{submission_id}")
async def get_submission(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Get a specific compliance submission"""
    submission = db.query(ComplianceSubmission).filter(ComplianceSubmission.id == submission_id).first()
    
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found"
        )
    
    return {
        "id": submission.id,
        "society_id": submission.society_id,
        "requirement_id": submission.requirement_id,
        "requirement": {
            "id": submission.requirement.id if submission.requirement else None,
            "name": submission.requirement.name if submission.requirement else None,
        },
        "applicable_period": submission.applicable_period,
        "due_date": submission.due_date.isoformat() if submission.due_date else None,
        "submission_date": submission.submission_date.isoformat() if submission.submission_date else None,
        "status": submission.status.value,
        "submitted_documents": submission.submitted_documents or [],
        "verification_notes": submission.verification_notes,
        "notes": submission.notes,
        "created_at": submission.created_at.isoformat() if submission.created_at else None,
    }


@router.post("/submissions")
async def create_submission(
    submission_data: ComplianceSubmissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new compliance submission"""
    # Verify requirement exists
    requirement = db.query(ComplianceRequirement).filter(ComplianceRequirement.id == submission_data.requirement_id).first()
    if not requirement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Compliance requirement not found"
        )
    
    # If user is society admin, get their society
    society_id = None
    if current_user.role == "society_admin":
        society = db.query(Society).filter(Society.admin_user_id == current_user.id).first()
        if not society:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Society profile not found"
            )
        society_id = society.id
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only society admins can create compliance submissions"
        )
    
    # Parse due date
    try:
        due_date = datetime.strptime(submission_data.due_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use YYYY-MM-DD"
        )
    
    new_submission = ComplianceSubmission(
        society_id=society_id,
        requirement_id=submission_data.requirement_id,
        applicable_period=submission_data.applicable_period,
        due_date=due_date,
        submitted_documents=submission_data.submitted_documents or [],
        notes=submission_data.notes,
        status=SubmissionStatus.NOT_STARTED
    )
    
    db.add(new_submission)
    db.commit()
    db.refresh(new_submission)
    
    return {
        "success": True,
        "message": "Compliance submission created successfully",
        "submission": {
            "id": new_submission.id,
            "requirement_id": new_submission.requirement_id,
            "status": new_submission.status.value,
        }
    }


@router.put("/submissions/{submission_id}")
async def update_submission(
    submission_id: int,
    submission_data: ComplianceSubmissionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a compliance submission"""
    submission = db.query(ComplianceSubmission).filter(ComplianceSubmission.id == submission_id).first()
    
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found"
        )
    
    # Check permissions
    if current_user.role == "society_admin":
        society = db.query(Society).filter(Society.admin_user_id == current_user.id).first()
        if not society or submission.society_id != society.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own society's submissions"
            )
    
    # Update fields
    if submission_data.applicable_period is not None:
        submission.applicable_period = submission_data.applicable_period
    if submission_data.due_date is not None:
        try:
            submission.due_date = datetime.strptime(submission_data.due_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD"
            )
    if submission_data.submitted_documents is not None:
        submission.submitted_documents = submission_data.submitted_documents
    if submission_data.notes is not None:
        submission.notes = submission_data.notes
    if submission_data.status is not None:
        try:
            submission.status = SubmissionStatus(submission_data.status)
            if submission.status == SubmissionStatus.SUBMITTED and not submission.submission_date:
                submission.submission_date = date.today()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Valid statuses: {[e.value for e in SubmissionStatus]}"
            )
    
    # Admin can add verification notes
    if submission_data.verification_notes is not None and current_user.role in ["admin", "super_admin", "mahasewa_admin"]:
        submission.verification_notes = submission_data.verification_notes
        if not submission.verified_by_user_id:
            submission.verified_by_user_id = current_user.id
            submission.verification_date = date.today()
    
    db.commit()
    db.refresh(submission)
    
    return {
        "success": True,
        "message": "Compliance submission updated successfully",
        "submission": {
            "id": submission.id,
            "status": submission.status.value,
        }
    }


@router.post("/submissions/{submission_id}/verify")
async def verify_submission(
    submission_id: int,
    verification_notes: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Verify a compliance submission (admin only)"""
    submission = db.query(ComplianceSubmission).filter(ComplianceSubmission.id == submission_id).first()
    
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found"
        )
    
    submission.status = SubmissionStatus.VERIFIED
    submission.verified_by_user_id = current_user.id
    submission.verification_date = date.today()
    if verification_notes:
        submission.verification_notes = verification_notes
    
    db.commit()
    db.refresh(submission)
    
    return {
        "success": True,
        "message": "Compliance submission verified successfully",
        "submission": {
            "id": submission.id,
            "status": submission.status.value,
            "verification_date": submission.verification_date.isoformat() if submission.verification_date else None,
        }
    }
