"""
File upload endpoints for images and documents
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
from sqlalchemy.orm import Session
from typing import Optional, List
import logging
from pathlib import Path
import uuid
from datetime import datetime

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.services.s3_service import file_storage
from app.config import settings
from app.middleware.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter()


def get_file_extension(filename: str) -> str:
    """Get file extension from filename"""
    return Path(filename).suffix.lower().lstrip('.')


def is_allowed_file(filename: str) -> bool:
    """Check if file extension is allowed"""
    ext = get_file_extension(filename)
    return ext in settings.ALLOWED_EXTENSIONS


def generate_unique_filename(original_filename: str) -> str:
    """Generate unique filename with timestamp and UUID"""
    ext = get_file_extension(original_filename)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    return f"{timestamp}_{unique_id}.{ext}"


@router.post("/upload/image")
@limiter.limit("20/minute")  # Limit image uploads to prevent abuse
async def upload_image(
    request: Request,
    file: UploadFile = File(...),
    category: Optional[str] = Form(None),
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload an image file
    
    Categories: gallery, blog, avatar, document
    """
    # Validate file
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided"
        )
    
    if not is_allowed_file(file.filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )
    
    # Check file size (50MB max)
    file_content = await file.read()
    file_size_mb = len(file_content) / (1024 * 1024)
    if file_size_mb > settings.MAX_UPLOAD_SIZE_MB:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE_MB}MB"
        )
    
    # Determine subdirectory based on category
    subdirectory = category or 'uploads'
    if category == 'gallery':
        subdirectory = 'gallery'
    elif category == 'blog':
        subdirectory = 'blog'
    elif category == 'avatar':
        subdirectory = 'avatars'
    else:
        subdirectory = 'uploads'
    
    # Generate unique filename
    unique_filename = generate_unique_filename(file.filename)
    file_path = f"{subdirectory}/{unique_filename}"
    
    # Upload file
    url = file_storage.upload_file(
        file_content=file_content,
        file_path=unique_filename,
        subdirectory=subdirectory
    )
    
    if not url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload file"
        )
    
    return {
        "success": True,
        "message": "File uploaded successfully",
        "url": url,
        "filename": unique_filename,
        "original_filename": file.filename,
        "size": len(file_content),
        "category": category
    }


@router.post("/upload/document")
@limiter.limit("10/minute")  # Limit document uploads to prevent abuse
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    document_type: Optional[str] = Form(None),
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload a document file (PDF, DOC, DOCX, etc.)
    """
    # Validate file
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided"
        )
    
    if not is_allowed_file(file.filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )
    
    # Check file size
    file_content = await file.read()
    file_size_mb = len(file_content) / (1024 * 1024)
    if file_size_mb > settings.MAX_UPLOAD_SIZE_MB:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE_MB}MB"
        )
    
    # Generate unique filename
    unique_filename = generate_unique_filename(file.filename)
    
    # Upload file
    url = file_storage.upload_file(
        file_content=file_content,
        file_path=unique_filename,
        subdirectory='documents'
    )
    
    if not url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload file"
        )
    
    return {
        "success": True,
        "message": "Document uploaded successfully",
        "url": url,
        "filename": unique_filename,
        "original_filename": file.filename,
        "size": len(file_content),
        "document_type": document_type
    }


@router.post("/upload/multiple")
async def upload_multiple_files(
    files: List[UploadFile] = File(...),
    category: Optional[str] = Form(None),
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload multiple files at once
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided"
        )
    
    results = []
    
    for file in files:
        try:
            if not file.filename or not is_allowed_file(file.filename):
                results.append({
                    "success": False,
                    "filename": file.filename,
                    "error": "Invalid file type or missing filename"
                })
                continue
            
            file_content = await file.read()
            file_size_mb = len(file_content) / (1024 * 1024)
            
            if file_size_mb > settings.MAX_UPLOAD_SIZE_MB:
                results.append({
                    "success": False,
                    "filename": file.filename,
                    "error": f"File too large (max {settings.MAX_UPLOAD_SIZE_MB}MB)"
                })
                continue
            
            # Determine subdirectory
            subdirectory = category or 'uploads'
            if category == 'gallery':
                subdirectory = 'gallery'
            elif category == 'blog':
                subdirectory = 'blog'
            
            # Generate unique filename
            unique_filename = generate_unique_filename(file.filename)
            
            # Upload file
            url = file_storage.upload_file(
                file_content=file_content,
                file_path=unique_filename,
                subdirectory=subdirectory
            )
            
            if url:
                results.append({
                    "success": True,
                    "filename": file.filename,
                    "url": url,
                    "size": len(file_content)
                })
            else:
                results.append({
                    "success": False,
                    "filename": file.filename,
                    "error": "Upload failed"
                })
                
        except Exception as e:
            logger.error(f"Error uploading file {file.filename}: {e}")
            results.append({
                "success": False,
                "filename": file.filename,
                "error": str(e)
            })
    
    return {
        "success": True,
        "message": f"Processed {len(files)} files",
        "results": results
    }


@router.delete("/upload/{file_path:path}")
async def delete_uploaded_file(
    file_path: str,
    subdirectory: str = 'uploads',
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete an uploaded file
    """
    # TODO: Add admin role check
    
    success = file_storage.delete_file(file_path, subdirectory)
    
    if success:
        return {
            "success": True,
            "message": "File deleted successfully"
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found or could not be deleted"
        )

