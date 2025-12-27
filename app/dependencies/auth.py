"""
Authentication dependencies for FastAPI
"""
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional

from app.db.session import get_db
from app.models.user import User
from app.utils.auth import decode_access_token
from app.schemas.auth import TokenData

security = HTTPBearer(auto_error=False)  # Don't auto-raise error, check cookie first


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token
    Supports both Authorization header and httpOnly cookie
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = None
    
    # Try to get token from Authorization header first
    if credentials:
        token = credentials.credentials
    else:
        # Fallback to httpOnly cookie
        token = request.cookies.get("access_token")
    
    if not token:
        raise credentials_exception
    
    payload = decode_access_token(token)
    
    if payload is None:
        raise credentials_exception
    
    email: str = payload.get("sub")
    user_id: int = payload.get("user_id")
    
    if email is None or user_id is None:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == user_id, User.email == email).first()
    
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


def require_role(required_role: str):
    """
    Dependency factory for role-based access control
    Usage: Depends(require_role("admin"))
    """
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role != required_role and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {required_role}"
            )
        return current_user
    
    return role_checker


def require_any_role(*allowed_roles: str):
    """
    Dependency factory for multiple allowed roles
    Usage: Depends(require_any_role("admin", "society_admin"))
    """
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        # Super admin and mahasewa_admin have access to everything
        admin_roles = ["super_admin", "mahasewa_admin"]
        if current_user.role in admin_roles:
            return current_user
        
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(allowed_roles)}"
            )
        return current_user
    
    return role_checker


# ============ ROLE-SPECIFIC DEPENDENCIES ============

async def get_current_member_user(
    current_user: Optional[User] = Depends(get_current_user)
) -> User:
    """Dependency to get current member user"""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Admin roles have access to everything
    admin_roles = ["super_admin", "mahasewa_admin", "mahasewa_staff"]
    if current_user.role in admin_roles:
        return current_user
    
    # Check if user is a member
    if current_user.role != "mahasewa_member":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Member role required."
        )
    
    return current_user


async def get_current_society_admin_user(
    current_user: Optional[User] = Depends(get_current_user)
) -> User:
    """Dependency to get current society admin user"""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Admin roles have access to everything
    admin_roles = ["super_admin", "mahasewa_admin", "mahasewa_staff"]
    if current_user.role in admin_roles:
        return current_user
    
    # Check if user is a society admin
    if current_user.role != "society_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Society admin role required."
        )
    
    return current_user


async def get_current_provider_user(
    current_user: Optional[User] = Depends(get_current_user)
) -> User:
    """Dependency to get current service provider user"""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Admin roles have access to everything
    admin_roles = ["super_admin", "mahasewa_admin", "mahasewa_staff"]
    if current_user.role in admin_roles:
        return current_user
    
    # Check if user is a service provider
    if current_user.role != "service_provider":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Service provider role required."
        )
    
    return current_user


async def get_current_branch_manager_user(
    current_user: Optional[User] = Depends(get_current_user)
) -> User:
    """Dependency to get current branch manager user"""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Super admin and mahasewa_admin have access to everything
    super_admin_roles = ["super_admin", "mahasewa_admin"]
    if current_user.role in super_admin_roles:
        return current_user
    
    # Check if user is a branch manager
    if current_user.role != "branch_manager":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Branch manager role required."
        )
    
    return current_user


async def get_current_staff_user(
    current_user: Optional[User] = Depends(get_current_user)
) -> User:
    """Dependency to get current staff user"""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Super admin and mahasewa_admin have access to everything
    super_admin_roles = ["super_admin", "mahasewa_admin"]
    if current_user.role in super_admin_roles:
        return current_user
    
    # Check if user is staff
    if current_user.role != "mahasewa_staff":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Staff role required."
        )
    
    return current_user

