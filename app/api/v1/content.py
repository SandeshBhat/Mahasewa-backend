"""Content endpoints for blog, events, downloads, FAQ"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel

from app.db.session import get_db
from app.models.content import BlogPost, Event, Download, FAQ, BlogStatus, PurchaseHistory, Gallery, EventType, EventStatus
from app.models.user import User
from app.dependencies.auth import get_current_user
from app.api.v1.admin import get_current_admin_user

router = APIRouter()


# ============ BLOG POSTS ============

class BlogPostCreate(BaseModel):
    """Request schema for creating a blog post"""
    title: str
    content: str
    excerpt: Optional[str] = None
    author: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    is_published: bool = False
    featured_image_url: Optional[str] = None


class BlogPostUpdate(BaseModel):
    """Request schema for updating a blog post"""
    title: Optional[str] = None
    content: Optional[str] = None
    excerpt: Optional[str] = None
    author: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    is_published: Optional[bool] = None
    featured_image_url: Optional[str] = None


@router.get("/blog-posts")
async def list_blog_posts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    published_only: bool = False,
    category: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List blog posts"""
    query = db.query(BlogPost)
    
    if published_only:
        query = query.filter(BlogPost.status == BlogStatus.PUBLISHED)
    
    if category:
        query = query.filter(BlogPost.category == category)
    
    if search:
        query = query.filter(
            BlogPost.title.ilike(f"%{search}%") |
            BlogPost.content.ilike(f"%{search}%")
        )
    
    total = query.count()
    posts = query.order_by(BlogPost.created_at.desc()).offset(skip).limit(limit).all()
    
    return {
        "posts": [
            {
                "id": p.id,
                "title": p.title,
                "excerpt": p.excerpt,
                "author": p.author,
                "category": p.category,
                "tags": p.tags or [],
                "is_published": p.status == BlogStatus.PUBLISHED,
                "status": p.status.value,
                "featured_image_url": p.featured_image_url,
                "views": p.views_count or 0,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            }
            for p in posts
        ],
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/blog-posts/{post_id}")
async def get_blog_post(
    post_id: int,
    db: Session = Depends(get_db)
):
    """Get blog post details"""
    post = db.query(BlogPost).filter(BlogPost.id == post_id).first()
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blog post not found"
        )
    
    # Increment views
    post.views_count = (post.views_count or 0) + 1
    db.commit()
    
    return {
        "id": post.id,
        "title": post.title,
        "content": post.content,
        "excerpt": post.excerpt,
        "author": post.author.full_name if post.author else None,
        "category": post.category,
        "tags": post.tags or [],
        "is_published": post.status == BlogStatus.PUBLISHED,
        "status": post.status.value,
        "featured_image_url": post.featured_image_url,
        "views": post.views_count or 0,
        "created_at": post.created_at.isoformat() if post.created_at else None,
        "updated_at": post.updated_at.isoformat() if post.updated_at else None,
    }


@router.post("/blog-posts")
async def create_blog_post(
    post_data: BlogPostCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Create a new blog post (admin only)"""
    
    import uuid
    from datetime import datetime
    
    # Generate slug from title
    slug = post_data.title.lower().replace(" ", "-").replace("_", "-")
    slug = "".join(c for c in slug if c.isalnum() or c == "-")
    slug = f"{slug}-{uuid.uuid4().hex[:8]}"
    
    new_post = BlogPost(
        title=post_data.title,
        slug=slug,
        content=post_data.content,
        excerpt=post_data.excerpt,
        author_user_id=current_user.id if current_user else 1,  # Default to admin user
        category=post_data.category,
        tags=post_data.tags or [],
        status=BlogStatus.PUBLISHED if post_data.is_published else BlogStatus.DRAFT,
        published_at=datetime.utcnow() if post_data.is_published else None,
        featured_image_url=post_data.featured_image_url,
        views_count=0
    )
    
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    
    return {
        "success": True,
        "message": "Blog post created successfully",
        "post": {
            "id": new_post.id,
            "title": new_post.title,
            "status": new_post.status.value
        }
    }


@router.put("/blog-posts/{post_id}")
async def update_blog_post(
    post_id: int,
    post_data: BlogPostUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Update a blog post (admin only)"""
    post = db.query(BlogPost).filter(BlogPost.id == post_id).first()
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blog post not found"
        )
    
    # Update fields
    if post_data.title is not None:
        post.title = post_data.title
    if post_data.content is not None:
        post.content = post_data.content
    if post_data.excerpt is not None:
        post.excerpt = post_data.excerpt
    if post_data.category is not None:
        post.category = post_data.category
    if post_data.tags is not None:
        post.tags = post_data.tags
    if post_data.is_published is not None:
        from datetime import datetime
        post.status = BlogStatus.PUBLISHED if post_data.is_published else BlogStatus.DRAFT
        if post_data.is_published and not post.published_at:
            post.published_at = datetime.utcnow()
    if post_data.featured_image_url is not None:
        post.featured_image_url = post_data.featured_image_url
    
    db.commit()
    db.refresh(post)
    
    return {
        "success": True,
        "message": "Blog post updated successfully",
        "post": {
            "id": post.id,
            "title": post.title
        }
    }


@router.delete("/blog-posts/{post_id}")
async def delete_blog_post(
    post_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Delete a blog post (admin only)"""
    post = db.query(BlogPost).filter(BlogPost.id == post_id).first()
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blog post not found"
        )
    
    db.delete(post)
    db.commit()
    
    return {
        "success": True,
        "message": "Blog post deleted successfully"
    }


# ============ ARTICLES (Alias for blog posts) ============

@router.get("/articles")
async def list_articles(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    published_only: bool = True,
    category: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List articles (alias for blog posts, published only by default)"""
    return await list_blog_posts(skip, limit, published_only, category, search, db)


# ============ FAQ ============

class FAQCreate(BaseModel):
    """Request schema for creating FAQ"""
    question: str
    answer: str
    category: Optional[str] = None
    order: Optional[int] = None
    is_active: Optional[bool] = True


class FAQUpdate(BaseModel):
    """Request schema for updating FAQ"""
    question: Optional[str] = None
    answer: Optional[str] = None
    category: Optional[str] = None
    order: Optional[int] = None
    is_active: Optional[bool] = None


@router.get("/faqs")
async def list_faqs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    category: Optional[str] = None,
    active_only: bool = False,
    db: Session = Depends(get_db)
):
    """List FAQs"""
    query = db.query(FAQ)
    
    if active_only:
        query = query.filter(FAQ.is_active == True)
    
    if category:
        query = query.filter(FAQ.category == category)
    
    total = query.count()
    faqs = query.order_by(FAQ.display_order.asc(), FAQ.created_at.asc()).offset(skip).limit(limit).all()
    
    return {
        "faqs": [
            {
                "id": f.id,
                "question": f.question,
                "answer": f.answer,
                "category": f.category,
                "order": f.display_order,
                "is_active": f.is_published,
                "created_at": f.created_at.isoformat() if f.created_at else None,
            }
            for f in faqs
        ],
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.post("/faqs")
async def create_faq(
    faq_data: FAQCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Create a new FAQ (admin only)"""
    new_faq = FAQ(
        question=faq_data.question,
        answer=faq_data.answer,
        category=faq_data.category,
        display_order=faq_data.order or 0,
        is_published=faq_data.is_active if faq_data.is_active is not None else True
    )
    
    db.add(new_faq)
    db.commit()
    db.refresh(new_faq)
    
    return {
        "success": True,
        "message": "FAQ created successfully",
        "faq": {
            "id": new_faq.id,
            "question": new_faq.question
        }
    }


@router.put("/faqs/{faq_id}")
async def update_faq(
    faq_id: int,
    faq_data: FAQUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Update an FAQ (admin only)"""
    faq = db.query(FAQ).filter(FAQ.id == faq_id).first()
    
    if not faq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="FAQ not found"
        )
    
    if faq_data.question is not None:
        faq.question = faq_data.question
    if faq_data.answer is not None:
        faq.answer = faq_data.answer
    if faq_data.category is not None:
        faq.category = faq_data.category
    if faq_data.order is not None:
        faq.display_order = faq_data.order
    if faq_data.is_active is not None:
        faq.is_published = faq_data.is_active
    
    db.commit()
    db.refresh(faq)
    
    return {
        "success": True,
        "message": "FAQ updated successfully",
        "faq": {
            "id": faq.id,
            "question": faq.question
        }
    }


@router.delete("/faqs/{faq_id}")
async def delete_faq(
    faq_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Delete an FAQ (admin only)"""
    faq = db.query(FAQ).filter(FAQ.id == faq_id).first()
    
    if not faq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="FAQ not found"
        )
    
    db.delete(faq)
    db.commit()
    
    return {
        "success": True,
        "message": "FAQ deleted successfully"
    }


# ============ DOWNLOADS ============

class DownloadCreate(BaseModel):
    """Request schema for creating download"""
    title: str
    description: Optional[str] = None
    file_url: str
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    cover_image_url: Optional[str] = None
    is_free: bool = True
    price: Optional[float] = 0
    member_discount_percent: Optional[int] = 0
    premium_discount_percent: Optional[int] = 0
    access_level: Optional[str] = 'public'
    requires_membership: bool = False
    tags: Optional[list] = None
    published_date: Optional[str] = None
    author: Optional[str] = None
    language: Optional[str] = 'en'
    is_active: bool = True


class DownloadUpdate(BaseModel):
    """Request schema for updating download"""
    title: Optional[str] = None
    description: Optional[str] = None
    file_url: Optional[str] = None
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    cover_image_url: Optional[str] = None
    is_free: Optional[bool] = None
    price: Optional[float] = None
    member_discount_percent: Optional[int] = None
    premium_discount_percent: Optional[int] = None
    access_level: Optional[str] = None
    requires_membership: Optional[bool] = None
    tags: Optional[list] = None
    published_date: Optional[str] = None
    author: Optional[str] = None
    language: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("/downloads")
async def list_downloads(
    skip: int = Query(0, ge=0),
    limit: int = Query(500, ge=1, le=500),
    category: Optional[str] = None,
    active_only: bool = False,
    db: Session = Depends(get_db)
):
    """List downloads"""
    query = db.query(Download)
    
    if active_only:
        query = query.filter(Download.is_active == True)
    
    if category:
        query = query.filter(Download.category == category)
    
    total = query.count()
    downloads = query.order_by(Download.created_at.desc()).offset(skip).limit(limit).all()
    
    return {
        "downloads": [
            {
                "id": d.id,
                "title": d.title,
                "description": d.description,
                "category": d.category,
                "subcategory": d.subcategory,
                "file_url": d.file_url,
                "file_type": d.file_type,
                "file_size": d.file_size,
                "cover_image_url": d.cover_image_url,
                "is_free": d.is_free,
                "price": float(d.price) if d.price else 0,
                "member_discount_percent": d.member_discount_percent or 0,
                "premium_discount_percent": d.premium_discount_percent or 0,
                "access_level": d.access_level or 'public',
                "requires_membership": d.requires_membership,
                "is_active": d.is_active,
                "download_count": d.download_count or 0,
                "purchase_count": d.purchase_count or 0,
                "total_revenue": float(d.total_revenue) if d.total_revenue else 0,
                "tags": d.tags or [],
                "published_date": d.published_date.isoformat() if d.published_date else None,
                "author": d.author,
                "language": d.language or 'en',
                "created_at": d.created_at.isoformat() if d.created_at else None,
                "updated_at": d.updated_at.isoformat() if d.updated_at else None,
            }
            for d in downloads
        ],
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.post("/downloads")
async def create_download(
    download_data: DownloadCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Create a new download (admin only)"""
    from decimal import Decimal
    
    published_date = None
    if download_data.published_date:
        try:
            published_date = datetime.fromisoformat(download_data.published_date.replace('Z', '+00:00'))
        except:
            pass
    
    new_download = Download(
        title=download_data.title,
        description=download_data.description,
        file_url=download_data.file_url,
        file_type=download_data.file_type,
        file_size=download_data.file_size,
        category=download_data.category,
        subcategory=download_data.subcategory,
        cover_image_url=download_data.cover_image_url,
        is_free=download_data.is_free,
        price=Decimal(str(download_data.price)) if download_data.price else Decimal('0'),
        member_discount_percent=download_data.member_discount_percent or 0,
        premium_discount_percent=download_data.premium_discount_percent or 0,
        access_level=download_data.access_level or 'public',
        requires_membership=download_data.requires_membership,
        tags=download_data.tags,
        published_date=published_date,
        author=download_data.author,
        language=download_data.language or 'en',
        is_active=download_data.is_active,
        download_count=0,
        purchase_count=0,
        total_revenue=Decimal('0')
    )
    
    db.add(new_download)
    db.commit()
    db.refresh(new_download)
    
    return {
        "success": True,
        "message": "Download created successfully",
        "download": {
            "id": new_download.id,
            "title": new_download.title
        }
    }


@router.put("/downloads/{download_id}")
async def update_download(
    download_id: int,
    download_data: DownloadUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Update a download (admin only)"""
    download = db.query(Download).filter(Download.id == download_id).first()
    
    if not download:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Download not found"
        )
    
    if download_data.title is not None:
        download.title = download_data.title
    if download_data.description is not None:
        download.description = download_data.description
    if download_data.file_url is not None:
        download.file_url = download_data.file_url
    if download_data.file_type is not None:
        download.file_type = download_data.file_type
    if download_data.file_size is not None:
        download.file_size = download_data.file_size
    if download_data.category is not None:
        download.category = download_data.category
    if download_data.subcategory is not None:
        download.subcategory = download_data.subcategory
    if download_data.cover_image_url is not None:
        download.cover_image_url = download_data.cover_image_url
    if download_data.is_free is not None:
        download.is_free = download_data.is_free
    if download_data.price is not None:
        from decimal import Decimal
        download.price = Decimal(str(download_data.price))
    if download_data.member_discount_percent is not None:
        download.member_discount_percent = download_data.member_discount_percent
    if download_data.premium_discount_percent is not None:
        download.premium_discount_percent = download_data.premium_discount_percent
    if download_data.access_level is not None:
        download.access_level = download_data.access_level
    if download_data.requires_membership is not None:
        download.requires_membership = download_data.requires_membership
    if download_data.tags is not None:
        download.tags = download_data.tags
    if download_data.published_date is not None:
        try:
            download.published_date = datetime.fromisoformat(download_data.published_date.replace('Z', '+00:00'))
        except:
            pass
    if download_data.author is not None:
        download.author = download_data.author
    if download_data.language is not None:
        download.language = download_data.language
    if download_data.is_active is not None:
        download.is_active = download_data.is_active
    
    db.commit()
    db.refresh(download)
    
    return {
        "success": True,
        "message": "Download updated successfully",
        "download": {
            "id": download.id,
            "title": download.title
        }
    }


@router.get("/downloads/{download_id}")
async def get_download(
    download_id: int,
    db: Session = Depends(get_db)
):
    """Get a single download by ID"""
    download = db.query(Download).filter(Download.id == download_id).first()
    
    if not download:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Download not found"
        )
    
    return {
        "download": {
            "id": download.id,
            "title": download.title,
            "description": download.description,
            "category": download.category,
            "subcategory": download.subcategory,
            "file_url": download.file_url,
            "file_type": download.file_type,
            "file_size": download.file_size,
            "cover_image_url": download.cover_image_url,
            "is_free": download.is_free,
            "price": float(download.price) if download.price else 0,
            "member_discount_percent": download.member_discount_percent or 0,
            "premium_discount_percent": download.premium_discount_percent or 0,
            "access_level": download.access_level or 'public',
            "requires_membership": download.requires_membership,
            "is_active": download.is_active,
            "download_count": download.download_count or 0,
            "purchase_count": download.purchase_count or 0,
            "total_revenue": float(download.total_revenue) if download.total_revenue else 0,
            "tags": download.tags or [],
            "published_date": download.published_date.isoformat() if download.published_date else None,
            "author": download.author,
            "language": download.language or 'en',
            "created_at": download.created_at.isoformat() if download.created_at else None,
            "updated_at": download.updated_at.isoformat() if download.updated_at else None,
        }
    }


@router.post("/downloads/{download_id}/download")
async def track_download(
    download_id: int,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Track a download"""
    download = db.query(Download).filter(Download.id == download_id).first()
    
    if not download:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Download not found"
        )
    
    # Increment download count
    download.download_count = (download.download_count or 0) + 1
    db.commit()
    
    return {"success": True, "message": "Download tracked"}


@router.delete("/downloads/{download_id}")
async def delete_download(
    download_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Delete a download (admin only)"""
    download = db.query(Download).filter(Download.id == download_id).first()
    
    if not download:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Download not found"
        )
    
    db.delete(download)
    db.commit()
    
    return {
        "success": True,
        "message": "Download deleted successfully"
    }


# ============ PURCHASES ============

class PurchaseCreate(BaseModel):
    """Request schema for creating purchase"""
    download_id: int
    amount: float


@router.get("/purchases")
async def list_purchases(
    user_id: Optional[int] = Query(None),
    download_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """List purchases"""
    query = db.query(PurchaseHistory)
    
    # Users can only see their own purchases unless admin
    if user_id and current_user:
        # Check if admin or same user
        is_admin = current_user.role in ['admin', 'super_admin', 'mahasewa_admin']
        if not is_admin and current_user.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view other users' purchases"
            )
        query = query.filter(PurchaseHistory.user_id == user_id)
    elif current_user and not user_id:
        # Default to current user's purchases
        query = query.filter(PurchaseHistory.user_id == current_user.id)
    
    if download_id:
        query = query.filter(PurchaseHistory.download_id == download_id)
    
    total = query.count()
    purchases = query.order_by(PurchaseHistory.created_at.desc()).offset(skip).limit(limit).all()
    
    # Get download details for each purchase
    purchases_with_details = []
    for purchase in purchases:
        download = db.query(Download).filter(Download.id == purchase.download_id).first()
        purchases_with_details.append({
            "id": purchase.id,
            "user_id": purchase.user_id,
            "download_id": purchase.download_id,
            "download_title": download.title if download else "Unknown",
            "download_category": download.category if download else None,
            "amount_paid": float(purchase.amount_paid),
            "currency": purchase.currency,
            "payment_method": purchase.payment_method,
            "payment_id": purchase.payment_id,
            "payment_status": purchase.payment_status,
            "invoice_number": purchase.invoice_number,
            "receipt_url": purchase.receipt_url,
            "access_granted_at": purchase.access_granted_at.isoformat() if purchase.access_granted_at else None,
            "expires_at": purchase.expires_at.isoformat() if purchase.expires_at else None,
            "download_count": purchase.download_count or 0,
            "last_downloaded_at": purchase.last_downloaded_at.isoformat() if purchase.last_downloaded_at else None,
            "created_at": purchase.created_at.isoformat() if purchase.created_at else None,
        })
    
    return {
        "purchases": purchases_with_details,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.post("/purchases")
async def create_purchase(
    purchase_data: PurchaseCreate,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a purchase (initiate payment)"""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Check if already purchased
    existing = db.query(PurchaseHistory).filter(
        PurchaseHistory.user_id == current_user.id,
        PurchaseHistory.download_id == purchase_data.download_id,
        PurchaseHistory.payment_status == 'completed'
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already purchased"
        )
    
    # Get download
    download = db.query(Download).filter(Download.id == purchase_data.download_id).first()
    if not download:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Download not found"
        )
    
    from decimal import Decimal
    from datetime import datetime
    
    # Create purchase record
    new_purchase = PurchaseHistory(
        user_id=current_user.id,
        download_id=purchase_data.download_id,
        amount_paid=Decimal(str(purchase_data.amount)),
        currency='INR',
        payment_status='pending',
        access_granted_at=None,
        download_count=0
    )
    
    db.add(new_purchase)
    db.commit()
    db.refresh(new_purchase)
    
    # TODO: Generate payment URL (Razorpay/PayU/Stripe integration)
    # For now, return purchase ID
    payment_url = None  # Will be set by payment gateway integration
    
    return {
        "success": True,
        "message": "Purchase initiated",
        "purchase": {
            "id": new_purchase.id,
            "payment_url": payment_url,
            "amount": float(new_purchase.amount_paid)
        }
    }


@router.post("/purchases/{purchase_id}/download")
async def track_purchase_download(
    purchase_id: int,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Track download from purchase"""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    purchase = db.query(PurchaseHistory).filter(
        PurchaseHistory.id == purchase_id,
        PurchaseHistory.user_id == current_user.id
    ).first()
    
    if not purchase:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Purchase not found"
        )
    
    # Update download count
    purchase.download_count = (purchase.download_count or 0) + 1
    purchase.last_downloaded_at = datetime.utcnow()
    db.commit()
    
    return {"success": True, "message": "Download tracked"}


# ============ GALLERY ============

class GalleryCreate(BaseModel):
    """Request schema for creating gallery item"""
    title: Optional[str] = None
    description: Optional[str] = None
    image_url: str
    thumbnail_url: Optional[str] = None
    category: Optional[str] = None
    album: Optional[str] = None
    tags: Optional[list] = None
    event_date: Optional[str] = None
    location: Optional[str] = None
    photographer: Optional[str] = None
    display_order: int = 0
    is_featured: bool = False
    is_active: bool = True


@router.get("/gallery")
async def list_gallery(
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=200),
    category: Optional[str] = None,
    album: Optional[str] = None,
    featured_only: bool = False,
    active_only: bool = False,
    db: Session = Depends(get_db)
):
    """List gallery items"""
    query = db.query(Gallery)
    
    if active_only:
        query = query.filter(Gallery.is_active == True)
    
    if featured_only:
        query = query.filter(Gallery.is_featured == True)
    
    if category:
        query = query.filter(Gallery.category == category)
    
    if album:
        query = query.filter(Gallery.album == album)
    
    total = query.count()
    gallery_items = query.order_by(Gallery.display_order, Gallery.created_at.desc()).offset(skip).limit(limit).all()
    
    return {
        "gallery": [
            {
                "id": g.id,
                "title": g.title,
                "description": g.description,
                "image_url": g.image_url,
                "thumbnail_url": g.thumbnail_url,
                "category": g.category,
                "album": g.album,
                "tags": g.tags or [],
                "event_date": g.event_date.isoformat() if g.event_date else None,
                "location": g.location,
                "photographer": g.photographer,
                "display_order": g.display_order,
                "is_featured": g.is_featured,
                "is_active": g.is_active,
                "view_count": g.view_count or 0,
                "created_at": g.created_at.isoformat() if g.created_at else None,
            }
            for g in gallery_items
        ],
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.post("/gallery")
async def create_gallery_item(
    gallery_data: GalleryCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Create a new gallery item (admin only)"""
    from datetime import datetime
    
    event_date = None
    if gallery_data.event_date:
        try:
            event_date = datetime.fromisoformat(gallery_data.event_date.replace('Z', '+00:00'))
        except:
            pass
    
    new_gallery = Gallery(
        title=gallery_data.title,
        description=gallery_data.description,
        image_url=gallery_data.image_url,
        thumbnail_url=gallery_data.thumbnail_url,
        category=gallery_data.category,
        album=gallery_data.album,
        tags=gallery_data.tags,
        event_date=event_date,
        location=gallery_data.location,
        photographer=gallery_data.photographer,
        display_order=gallery_data.display_order or 0,
        is_featured=gallery_data.is_featured,
        is_active=gallery_data.is_active,
        view_count=0
    )
    
    db.add(new_gallery)
    db.commit()
    db.refresh(new_gallery)
    
    return {
        "success": True,
        "message": "Gallery item created successfully",
        "gallery": {
            "id": new_gallery.id,
            "title": new_gallery.title
        }
    }


@router.get("/gallery/{gallery_id}")
async def get_gallery_item(
    gallery_id: int,
    db: Session = Depends(get_db)
):
    """Get a single gallery item by ID"""
    gallery = db.query(Gallery).filter(Gallery.id == gallery_id).first()
    
    if not gallery:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gallery item not found"
        )
    
    return {
        "gallery": {
            "id": gallery.id,
            "title": gallery.title,
            "description": gallery.description,
            "image_url": gallery.image_url,
            "thumbnail_url": gallery.thumbnail_url,
            "category": gallery.category,
            "album": gallery.album,
            "tags": gallery.tags or [],
            "event_date": gallery.event_date.isoformat() if gallery.event_date else None,
            "location": gallery.location,
            "photographer": gallery.photographer,
            "display_order": gallery.display_order,
            "is_featured": gallery.is_featured,
            "is_active": gallery.is_active,
            "view_count": gallery.view_count or 0,
            "created_at": gallery.created_at.isoformat() if gallery.created_at else None,
        }
    }


@router.put("/gallery/{gallery_id}")
async def update_gallery_item(
    gallery_id: int,
    gallery_data: GalleryCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Update a gallery item (admin only)"""
    gallery = db.query(Gallery).filter(Gallery.id == gallery_id).first()
    
    if not gallery:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gallery item not found"
        )
    
    from datetime import datetime
    
    if gallery_data.title is not None:
        gallery.title = gallery_data.title
    if gallery_data.description is not None:
        gallery.description = gallery_data.description
    if gallery_data.image_url is not None:
        gallery.image_url = gallery_data.image_url
    if gallery_data.thumbnail_url is not None:
        gallery.thumbnail_url = gallery_data.thumbnail_url
    if gallery_data.category is not None:
        gallery.category = gallery_data.category
    if gallery_data.album is not None:
        gallery.album = gallery_data.album
    if gallery_data.tags is not None:
        gallery.tags = gallery_data.tags
    if gallery_data.event_date is not None:
        try:
            gallery.event_date = datetime.fromisoformat(gallery_data.event_date.replace('Z', '+00:00'))
        except:
            pass
    if gallery_data.location is not None:
        gallery.location = gallery_data.location
    if gallery_data.photographer is not None:
        gallery.photographer = gallery_data.photographer
    if gallery_data.display_order is not None:
        gallery.display_order = gallery_data.display_order
    if gallery_data.is_featured is not None:
        gallery.is_featured = gallery_data.is_featured
    if gallery_data.is_active is not None:
        gallery.is_active = gallery_data.is_active
    
    db.commit()
    db.refresh(gallery)
    
    return {
        "success": True,
        "message": "Gallery item updated successfully",
        "gallery": {
            "id": gallery.id,
            "title": gallery.title
        }
    }


@router.delete("/gallery/{gallery_id}")
async def delete_gallery_item(
    gallery_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Delete a gallery item (admin only)"""
    gallery = db.query(Gallery).filter(Gallery.id == gallery_id).first()
    
    if not gallery:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gallery item not found"
        )
    
    db.delete(gallery)
    db.commit()
    
    return {
        "success": True,
        "message": "Gallery item deleted successfully"
    }


@router.post("/gallery/{gallery_id}/view")
async def track_gallery_view(
    gallery_id: int,
    db: Session = Depends(get_db)
):
    """Track gallery view"""
    gallery = db.query(Gallery).filter(Gallery.id == gallery_id).first()
    
    if not gallery:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gallery item not found"
        )
    
    gallery.view_count = (gallery.view_count or 0) + 1
    db.commit()
    
    return {"success": True, "message": "View tracked"}


# ============ EVENTS ============

class EventCreate(BaseModel):
    """Request schema for creating an event"""
    title: str
    description: Optional[str] = None
    event_type: str  # webinar, workshop, conference, seminar, meeting
    status: Optional[str] = "upcoming"  # upcoming, ongoing, completed, cancelled
    start_datetime: datetime
    end_datetime: datetime
    is_online: bool = False
    venue: Optional[str] = None
    venue_address: Optional[str] = None
    meeting_url: Optional[str] = None
    max_attendees: Optional[int] = None
    registration_fee: float = 0.0
    registration_deadline: Optional[datetime] = None
    is_registration_open: bool = True
    banner_image_url: Optional[str] = None
    organizer_user_id: int


class EventUpdate(BaseModel):
    """Request schema for updating an event"""
    title: Optional[str] = None
    description: Optional[str] = None
    event_type: Optional[str] = None
    status: Optional[str] = None
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    is_online: Optional[bool] = None
    venue: Optional[str] = None
    venue_address: Optional[str] = None
    meeting_url: Optional[str] = None
    max_attendees: Optional[int] = None
    registration_fee: Optional[float] = None
    registration_deadline: Optional[datetime] = None
    is_registration_open: Optional[bool] = None
    banner_image_url: Optional[str] = None
    organizer_user_id: Optional[int] = None


@router.get("/events")
async def list_events(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    event_type: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    upcoming_only: bool = False,
    db: Session = Depends(get_db)
):
    """List events"""
    query = db.query(Event)
    
    if event_type:
        try:
            event_type_enum = EventType(event_type.lower())
            query = query.filter(Event.event_type == event_type_enum)
        except ValueError:
            pass
    
    if status:
        try:
            status_enum = EventStatus(status.lower())
            query = query.filter(Event.status == status_enum)
        except ValueError:
            pass
    
    if upcoming_only:
        query = query.filter(Event.start_datetime >= datetime.utcnow())
    
    if search:
        query = query.filter(
            Event.title.ilike(f"%{search}%") |
            Event.description.ilike(f"%{search}%")
        )
    
    total = query.count()
    events = query.order_by(Event.start_datetime.asc()).offset(skip).limit(limit).all()
    
    return {
        "events": [
            {
                "id": e.id,
                "title": e.title,
                "description": e.description,
                "event_type": e.event_type.value if e.event_type else None,
                "status": e.status.value if e.status else None,
                "start_datetime": e.start_datetime.isoformat() if e.start_datetime else None,
                "end_datetime": e.end_datetime.isoformat() if e.end_datetime else None,
                "is_online": e.is_online,
                "venue": e.venue,
                "venue_address": e.venue_address,
                "meeting_url": e.meeting_url,
                "max_attendees": e.max_attendees,
                "registration_fee": float(e.registration_fee) if e.registration_fee else 0.0,
                "registration_deadline": e.registration_deadline.isoformat() if e.registration_deadline else None,
                "is_registration_open": e.is_registration_open,
                "banner_image_url": e.banner_image_url,
                "organizer_user_id": e.organizer_user_id,
                "total_registrations": e.total_registrations or 0,
                "total_attended": e.total_attended or 0,
                "created_at": e.created_at.isoformat() if e.created_at else None,
                "updated_at": e.updated_at.isoformat() if e.updated_at else None,
            }
            for e in events
        ],
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/events/{event_id}")
async def get_event(
    event_id: int,
    db: Session = Depends(get_db)
):
    """Get event details"""
    event = db.query(Event).filter(Event.id == event_id).first()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    return {
        "id": event.id,
        "title": event.title,
        "description": event.description,
        "event_type": event.event_type.value if event.event_type else None,
        "status": event.status.value if event.status else None,
        "start_datetime": event.start_datetime.isoformat() if event.start_datetime else None,
        "end_datetime": event.end_datetime.isoformat() if event.end_datetime else None,
        "is_online": event.is_online,
        "venue": event.venue,
        "venue_address": event.venue_address,
        "meeting_url": event.meeting_url,
        "max_attendees": event.max_attendees,
        "registration_fee": float(event.registration_fee) if event.registration_fee else 0.0,
        "registration_deadline": event.registration_deadline.isoformat() if event.registration_deadline else None,
        "is_registration_open": event.is_registration_open,
        "banner_image_url": event.banner_image_url,
        "organizer_user_id": event.organizer_user_id,
        "total_registrations": event.total_registrations or 0,
        "total_attended": event.total_attended or 0,
        "created_at": event.created_at.isoformat() if event.created_at else None,
        "updated_at": event.updated_at.isoformat() if event.updated_at else None,
    }


@router.post("/events")
async def create_event(
    event_data: EventCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Create a new event (admin only)"""
    
    # Generate slug from title
    import re
    slug = re.sub(r'[^a-z0-9]+', '-', event_data.title.lower()).strip('-')
    
    # Check if slug exists
    existing = db.query(Event).filter(Event.slug == slug).first()
    if existing:
        slug = f"{slug}-{int(datetime.utcnow().timestamp())}"
    
    try:
        event_type_enum = EventType(event_data.event_type.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid event_type: {event_data.event_type}"
        )
    
    try:
        status_enum = EventStatus(event_data.status.lower()) if event_data.status else EventStatus.UPCOMING
    except ValueError:
        status_enum = EventStatus.UPCOMING
    
    new_event = Event(
        title=event_data.title,
        slug=slug,
        description=event_data.description,
        event_type=event_type_enum,
        status=status_enum,
        start_datetime=event_data.start_datetime,
        end_datetime=event_data.end_datetime,
        is_online=event_data.is_online,
        venue=event_data.venue,
        venue_address=event_data.venue_address,
        meeting_url=event_data.meeting_url,
        max_attendees=event_data.max_attendees,
        registration_fee=event_data.registration_fee,
        registration_deadline=event_data.registration_deadline,
        is_registration_open=event_data.is_registration_open,
        banner_image_url=event_data.banner_image_url,
        organizer_user_id=event_data.organizer_user_id or (current_user.id if current_user else 1)
    )
    
    db.add(new_event)
    db.commit()
    db.refresh(new_event)
    
    return {
        "success": True,
        "message": "Event created successfully",
        "event": {
            "id": new_event.id,
            "title": new_event.title,
            "slug": new_event.slug
        }
    }


@router.put("/events/{event_id}")
async def update_event(
    event_id: int,
    event_data: EventUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Update an event (admin only)"""
    event = db.query(Event).filter(Event.id == event_id).first()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    if event_data.title is not None:
        event.title = event_data.title
        # Update slug if title changed
        import re
        slug = re.sub(r'[^a-z0-9]+', '-', event_data.title.lower()).strip('-')
        existing = db.query(Event).filter(Event.slug == slug, Event.id != event_id).first()
        if not existing:
            event.slug = slug
    
    if event_data.description is not None:
        event.description = event_data.description
    if event_data.event_type is not None:
        try:
            event.event_type = EventType(event_data.event_type.lower())
        except ValueError:
            pass
    if event_data.status is not None:
        try:
            event.status = EventStatus(event_data.status.lower())
        except ValueError:
            pass
    if event_data.start_datetime is not None:
        event.start_datetime = event_data.start_datetime
    if event_data.end_datetime is not None:
        event.end_datetime = event_data.end_datetime
    if event_data.is_online is not None:
        event.is_online = event_data.is_online
    if event_data.venue is not None:
        event.venue = event_data.venue
    if event_data.venue_address is not None:
        event.venue_address = event_data.venue_address
    if event_data.meeting_url is not None:
        event.meeting_url = event_data.meeting_url
    if event_data.max_attendees is not None:
        event.max_attendees = event_data.max_attendees
    if event_data.registration_fee is not None:
        event.registration_fee = event_data.registration_fee
    if event_data.registration_deadline is not None:
        event.registration_deadline = event_data.registration_deadline
    if event_data.is_registration_open is not None:
        event.is_registration_open = event_data.is_registration_open
    if event_data.banner_image_url is not None:
        event.banner_image_url = event_data.banner_image_url
    if event_data.organizer_user_id is not None:
        event.organizer_user_id = event_data.organizer_user_id
    
    db.commit()
    db.refresh(event)
    
    return {
        "success": True,
        "message": "Event updated successfully",
        "event": {
            "id": event.id,
            "title": event.title
        }
    }


@router.delete("/events/{event_id}")
async def delete_event(
    event_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Delete an event (admin only)"""
    event = db.query(Event).filter(Event.id == event_id).first()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    db.delete(event)
    db.commit()
    
    return {
        "success": True,
        "message": "Event deleted successfully"
    }
