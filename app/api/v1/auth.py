"""
Authentication endpoints for MahaSeWA API
"""
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.orm import Session
from datetime import timedelta, datetime

from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    UserLogin,
    UserRegister,
    Token,
    UserResponse,
    PasswordChange,
    PasswordReset,
    PasswordResetConfirm
)
from app.utils.auth import verify_password, get_password_hash, create_access_token
from app.dependencies.auth import get_current_user
from app.config import settings
from app.middleware.rate_limit import limiter

router = APIRouter()


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
@limiter.limit("3/hour")  # Stricter limit for registration (prevent spam)
async def register(
    request: Request,
    user_data: UserRegister, 
    response: Response, 
    db: Session = Depends(get_db)
):
    """
    Register a new user
    """
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    new_user = User(
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        phone=user_data.phone,
        role=user_data.role,
        is_active=True
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Create access token
    access_token = create_access_token(
        data={"sub": new_user.email, "user_id": new_user.id, "role": new_user.role}
    )
    
    # Set httpOnly cookie for secure token storage
    expires = datetime.utcnow() + timedelta(days=7)
    
    response.set_cookie(
        key="access_token",
        value=access_token,
        expires=expires,
        httponly=True,  # Prevents JavaScript access (XSS protection)
        secure=settings.ENVIRONMENT == "production",  # HTTPS only in production
        samesite="lax",  # CSRF protection
        path="/",
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse.from_orm(new_user)
    }


@router.post("/login", response_model=Token)
@limiter.limit("5/minute")  # Stricter limit for login (prevent brute force)
async def login(
    request: Request,
    credentials: UserLogin, 
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Login user and return JWT token
    Sets httpOnly cookie for secure token storage
    """
    # Normalize email to lowercase for case-insensitive lookup
    email_lower = credentials.email.strip().lower()
    user = db.query(User).filter(User.email.ilike(email_lower)).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )
    
    # Create access token
    access_token = create_access_token(
        data={"sub": user.email, "user_id": user.id, "role": user.role}
    )
    
    # Set httpOnly cookie for secure token storage
    # Cookie expires in 7 days (same as token expiration)
    expires = datetime.utcnow() + timedelta(days=7)
    
    response.set_cookie(
        key="access_token",
        value=access_token,
        expires=expires,
        httponly=True,  # Prevents JavaScript access (XSS protection)
        secure=settings.ENVIRONMENT == "production",  # HTTPS only in production
        samesite="lax",  # CSRF protection
        path="/",
    )
    
    # Also set token in response body for backward compatibility
    # Frontend should NOT store this in localStorage
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse.from_orm(user)
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current user information
    """
    return UserResponse.from_orm(current_user)


@router.put("/me", response_model=UserResponse)
async def update_current_user_info(
    user_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update current user's profile information
    """
    # Update allowed fields
    if "email" in user_data and user_data["email"]:
        # Check if email is already taken by another user
        existing = db.query(User).filter(
            User.email == user_data["email"],
            User.id != current_user.id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        current_user.email = user_data["email"]
    
    if "full_name" in user_data and user_data["full_name"] is not None:
        current_user.full_name = user_data["full_name"]
    
    if "phone" in user_data and user_data["phone"] is not None:
        current_user.phone = user_data["phone"]
    
    db.commit()
    db.refresh(current_user)
    
    return UserResponse.from_orm(current_user)


@router.post("/logout")
async def logout(response: Response):
    """
    Logout user by clearing httpOnly cookie
    """
    response.delete_cookie(
        key="access_token",
        path="/",
        samesite="lax"
    )
    return {"message": "Logged out successfully"}


@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Change user password
    """
    # Verify old password
    if not verify_password(password_data.old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect password"
        )
    
    # Update password
    current_user.password_hash = get_password_hash(password_data.new_password)
    db.commit()
    
    return {"message": "Password updated successfully"}


@router.post("/reset-password")
@limiter.limit("3/hour")  # Prevent abuse of password reset
async def request_password_reset(
    request: Request,
    reset_data: PasswordReset, 
    db: Session = Depends(get_db)
):
    """
    Request password reset (send email with reset link)
    """
    user = db.query(User).filter(User.email == reset_data.email).first()
    
    # Always return success to prevent email enumeration
    if user:
        reset_token = create_access_token(
            data={"sub": user.email, "type": "password_reset"},
            expires_delta=timedelta(hours=1)
        )
        # Send password reset email
        try:
            from app.services.email_service import EmailService
            EmailService.send_password_reset_email(user, reset_token)
        except Exception as e:
            # Log error but don't fail the request
            print(f"Error sending password reset email: {e}")
    
    return {"message": "If the email exists, a password reset link has been sent"}


@router.post("/reset-password/confirm")
async def confirm_password_reset(
    reset_data: PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    """
    Confirm password reset with token
    """
    from app.utils.auth import decode_access_token
    
    payload = decode_access_token(reset_data.token)
    if not payload or payload.get("type") != "password_reset":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    email = payload.get("sub")
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update password
    user.password_hash = get_password_hash(reset_data.new_password)
    db.commit()
    
    return {"message": "Password reset successfully"}


@router.get("/check-email/{email}")
async def check_email_exists(email: str, db: Session = Depends(get_db)):
    """
    Check if email exists (for registration validation)
    """
    user = db.query(User).filter(User.email == email).first()
    return {"exists": user is not None}
