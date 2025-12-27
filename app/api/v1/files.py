"""File serving endpoints for downloads and uploads"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
import os
from pathlib import Path

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.models.content import Download, PurchaseHistory
from app.models.member import Member
from app.config import settings

router = APIRouter()


@router.get("/downloads/{download_id}/file")
async def download_file(
    download_id: int,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Download a file by download ID
    
    Access control:
    - Free downloads: Anyone can download
    - Paid downloads: Must have purchased or be admin
    - Member-only downloads: Must be a member or admin
    """
    download = db.query(Download).filter(Download.id == download_id).first()
    
    if not download:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Download not found"
        )
    
    if not download.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Download is not active"
        )
    
    # Check access permissions
    admin_roles = ["super_admin", "mahasewa_admin", "mahasewa_staff"]
    is_admin = current_user and current_user.role in admin_roles
    
    # Free downloads - anyone can access
    if download.is_free:
        pass  # Allow access
    # Paid downloads - check purchase
    elif download.price and download.price > 0:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to download paid content"
            )
        
        if not is_admin:
            # Check if user has purchased this download
            purchase = db.query(PurchaseHistory).filter(
                PurchaseHistory.user_id == current_user.id,
                PurchaseHistory.download_id == download_id,
                PurchaseHistory.payment_status == "completed"
            ).first()
            
            if not purchase:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You must purchase this download before accessing it"
                )
    
    # Member-only downloads
    if download.requires_membership:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        if not is_admin:
            # Check if user is a member
            member = db.query(Member).filter(Member.user_id == current_user.id).first()
            if not member:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Membership required to download this file"
                )
    
    # Get file path
    file_url = download.file_url
    if not file_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # If file_url is a full URL, redirect to it
    if file_url.startswith("http://") or file_url.startswith("https://"):
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=file_url)
    
    # If file_url is a relative path, serve from uploads directory
    upload_base_dir = os.getenv("UPLOAD_BASE_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads"))
    file_path = os.path.join(upload_base_dir, file_url.lstrip("/"))
    
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found on server"
        )
    
    # Increment download count
    download.download_count = (download.download_count or 0) + 1
    db.commit()
    
    # Determine media type
    file_ext = Path(file_path).suffix.lower()
    media_types = {
        ".pdf": "application/pdf",
        ".doc": "application/msword",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".xls": "application/vnd.ms-excel",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".zip": "application/zip",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
    }
    media_type = media_types.get(file_ext, "application/octet-stream")
    
    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=download.title + file_ext,
        headers={
            "Content-Disposition": f'attachment; filename="{download.title}{file_ext}"'
        }
    )


@router.get("/uploads/{file_path:path}")
async def serve_uploaded_file(
    file_path: str,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Serve uploaded files
    
    Access control:
    - Public files: Anyone can access
    - Private files: Require authentication
    """
    upload_base_dir = os.getenv("UPLOAD_BASE_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads"))
    full_path = os.path.join(upload_base_dir, file_path)
    
    # Security: Prevent directory traversal
    full_path = os.path.normpath(full_path)
    if not full_path.startswith(os.path.normpath(upload_base_dir)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    if not os.path.exists(full_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Determine media type
    file_ext = Path(full_path).suffix.lower()
    media_types = {
        ".pdf": "application/pdf",
        ".doc": "application/msword",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
    }
    media_type = media_types.get(file_ext, "application/octet-stream")
    
    return FileResponse(
        path=full_path,
        media_type=media_type,
        filename=os.path.basename(full_path)
    )

