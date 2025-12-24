# 🔧 Remaining Backend Tasks

**Date:** December 5, 2025  
**Priority:** High - Required for full functionality

---

## 1. **Branch Analytics Endpoints** 🔴 HIGH PRIORITY

### **Endpoint 1: Get Branch Analytics**
```python
@router.get("/admin/branch-analytics")
async def get_branch_analytics(
    branch_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get branch analytics data"""
    # Aggregate data by branch:
    # - Total members per branch
    # - Total bookings per branch
    # - Total revenue per branch
    # - Total cases per branch
    # Return summary and branch-wise breakdown
```

**File to Create/Update:**
- `backend/app/api/v1/admin.py` or new `backend/app/api/v1/analytics.py`

---

### **Endpoint 2: Generate Branch Report**
```python
@router.get("/admin/branch-reports/generate")
async def generate_branch_report(
    branch_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    format: str = "excel",  # "excel" or "pdf"
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Generate branch report in Excel or PDF format"""
    # Generate report with all branch data
    # Return file for download
```

---

## 2. **Publication Ad Endpoints** 🔴 HIGH PRIORITY

### **Database Tables Needed:**

```python
# backend/app/models/publication_ad.py

class PublicationAd(Base, TimestampMixin):
    __tablename__ = "publication_ads"
    
    id = Column(Integer, primary_key=True)
    vendor_id = Column(Integer, ForeignKey("service_providers.id"))
    publication_issue = Column(String(100))  # e.g., "January 2025"
    page_color = Column(String(50))  # "bw", "color", "premium_color"
    page_size = Column(String(50))  # "full", "half", "quarter"
    position = Column(String(50))  # "front_cover", "back_cover", "inside"
    total_price = Column(Numeric(10, 2))
    ad_content = Column(Text)
    contact_name = Column(String(255))
    contact_email = Column(String(255))
    contact_phone = Column(String(20))
    notes = Column(Text)
    status = Column(String(50), default="pending")  # "pending", "approved", "rejected"
    deadline = Column(Date)
```

### **Endpoints Needed:**

#### **1. List Ad Bookings (Admin)**
```python
@router.get("/admin/publication-ads")
async def list_publication_ads(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """List all publication ad bookings"""
```

#### **2. Notify Vendors**
```python
@router.post("/admin/publication-ads/notify-vendors")
async def notify_vendors_about_ads(
    vendor_ids: List[int],
    subject: str,
    message: str,
    publication_issue: str,
    deadline: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Send notifications to vendors about ad opportunities"""
    # Create notifications for each vendor
    # Optionally send emails
```

#### **3. Book Ad (Vendor)**
```python
@router.post("/publication-ads/book")
async def book_publication_ad(
    ad_data: PublicationAdCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Vendor books a publication ad"""
    # Create ad booking
    # Generate invoice
```

#### **4. Get Vendor's Ad Bookings**
```python
@router.get("/publication-ads/my-bookings")
async def get_my_ad_bookings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's (vendor) ad bookings"""
```

---

## 3. **Database Schema Updates** 🔴 HIGH PRIORITY

### **Add `branch_id` to Tables:**

#### **Service Bookings:**
```python
# backend/app/models/booking.py
# Add to ServiceBooking model:
branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)
branch = relationship("Branch", backref="service_bookings")
```

#### **Consultations:**
```python
# backend/app/models/consultation.py
# Add to Consultation model:
branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)
branch = relationship("Branch", backref="consultations")
```

#### **Invoices:**
```python
# backend/app/models/invoice.py (if exists)
# Add to Invoice model:
branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)
branch = relationship("Branch", backref="invoices")
```

### **Migration Script:**
```python
# backend/alembic/versions/XXXX_add_branch_tracking.py
def upgrade():
    op.add_column('service_bookings', sa.Column('branch_id', sa.Integer(), nullable=True))
    op.add_column('consultations', sa.Column('branch_id', nullable=True))
    op.add_column('invoices', sa.Column('branch_id', nullable=True))
    op.create_foreign_key('fk_bookings_branch', 'service_bookings', 'branches', ['branch_id'], ['id'])
    op.create_foreign_key('fk_consultations_branch', 'consultations', 'branches', ['branch_id'], ['id'])
    op.create_foreign_key('fk_invoices_branch', 'invoices', 'branches', ['branch_id'], ['id'])
```

---

## 4. **Location Coordinates** 🟡 MEDIUM PRIORITY

### **Add to Service Providers:**
```python
# backend/app/models/provider.py
# Add to ServiceProvider model:
latitude = Column(Numeric(10, 7), nullable=True)
longitude = Column(Numeric(10, 7), nullable=True)
```

### **Add to Societies:**
```python
# backend/app/models/society.py
# Add to Society model:
latitude = Column(Numeric(10, 7), nullable=True)
longitude = Column(Numeric(10, 7), nullable=True)
```

### **Geocoding Service (Optional):**
```python
# backend/app/services/geocoding_service.py
async def geocode_address(address: str) -> Tuple[float, float]:
    """Convert address to coordinates using geocoding API"""
    # Use Google Maps API, OpenStreetMap, or similar
    pass
```

---

## 5. **Vendor Subscription Status in Provider Response** 🟡 MEDIUM PRIORITY

### **Update Provider Endpoint:**
```python
# backend/app/api/v1/providers.py
@router.get("/")
async def list_providers(...):
    # Include subscription status in response:
    # subscription_status = "basic" | "premium" | "elite" | "none"
    # subscription_active = True/False
    # subscription_expiry_date = date
```

---

## 6. **Razorpay Payment Endpoints** 🟡 MEDIUM PRIORITY (When Key Available)

### **Create Payment Order:**
```python
@router.post("/api/v1/payments/create-order")
async def create_payment_order(
    amount: float,
    currency: str = "INR",
    receipt: Optional[str] = None,
    notes: Optional[dict] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create Razorpay order"""
    # Initialize Razorpay client
    # Create order
    # Store order in database
    # Return order details
```

### **Verify Payment:**
```python
@router.post("/api/v1/payments/verify")
async def verify_payment(
    order_id: str,
    payment_id: str,
    signature: str,
    invoice_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Verify Razorpay payment signature"""
    # Verify signature
    # Update invoice/payment status
    # Trigger any post-payment actions
```

### **Webhook Handler:**
```python
@router.post("/api/v1/payments/webhook")
async def payment_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """Handle Razorpay webhook events"""
    # Verify webhook signature
    # Handle payment events (success, failure, refund)
    # Update payment status
```

---

## 7. **Invoice Generation Endpoints** 🟡 MEDIUM PRIORITY

### **Generate Invoice:**
```python
@router.post("/invoices/generate")
async def generate_invoice(
    invoice_data: InvoiceData,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate invoice"""
    # Create invoice record
    # Generate PDF (optional)
    # Send email (optional)
```

### **Send Invoice Email:**
```python
@router.post("/invoices/{invoice_id}/send-email")
async def send_invoice_email(
    invoice_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send invoice via email"""
    # Generate PDF
    # Send email with attachment
```

---

## 📋 **Implementation Priority**

1. **🔴 CRITICAL:**
   - Publication Ad endpoints (revenue generation)
   - Branch Analytics endpoints (reporting)
   - Add `branch_id` to bookings/consultations/invoices

2. **🟡 IMPORTANT:**
   - Location coordinates (latitude/longitude)
   - Subscription status in provider response
   - Invoice generation endpoints

3. **🟢 WHEN READY:**
   - Razorpay payment endpoints (when API key available)

---

## 🎯 **Quick Wins**

### **1. Add Subscription Status to Provider Response:**
```python
# In providers.py list_providers endpoint:
# Get active subscription for each provider
subscription = db.query(VendorSubscription).filter(
    VendorSubscription.service_provider_id == p.id,
    VendorSubscription.status == SubscriptionStatus.ACTIVE,
    VendorSubscription.end_date >= date.today()
).first()

subscription_status = subscription.plan.tier.value if subscription else "none"
```

### **2. Auto-set branch_id on Registration:**
```python
# In member registration endpoint:
# Determine branch based on city or user assignment
branch_id = determine_branch_for_member(city, user_id)
```

### **3. Add Location to Provider/Society Response:**
```python
# Include latitude/longitude in API responses
# Use city coordinates as fallback if not set
```

---

**Last Updated:** December 5, 2025
