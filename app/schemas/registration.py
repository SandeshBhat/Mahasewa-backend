"""Registration schemas for Society, Member, and Vendor"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import date


# ============ SOCIETY REGISTRATION ============

class SocietyRegistrationRequest(BaseModel):
    """Society registration request"""
    # Society details
    society_name: str = Field(..., min_length=3, max_length=255)
    registration_number: str = Field(..., min_length=3, max_length=100)
    date_of_formation: Optional[date] = None
    society_type: Optional[str] = None
    
    # Address
    address: str = Field(..., min_length=10)
    city: str
    state: str = "Maharashtra"
    pincode: str = Field(..., pattern=r'^\d{6}$')
    taluka: Optional[str] = None
    district: Optional[str] = None
    
    # Contact (Chairman/Secretary)
    chairman_name: str
    chairman_phone: str = Field(..., pattern=r'^\d{10}$')
    chairman_email: EmailStr
    secretary_name: Optional[str] = None
    secretary_phone: Optional[str] = None
    secretary_email: Optional[EmailStr] = None
    
    # Society details
    total_members: int = Field(0, ge=0)
    total_buildings: Optional[int] = Field(None, ge=0)
    total_flats: int = Field(0, ge=0)
    total_shops: int = Field(0, ge=0)
    total_garages: int = Field(0, ge=0)
    total_area: Optional[str] = None
    amenities: Optional[List[str]] = []
    
    # Legal status
    is_registered: bool = False
    has_deemed_conveyance: bool = False
    has_oc: bool = False
    has_cc: bool = False
    needs_legal_help: bool = False
    notes: Optional[str] = None
    
    # Membership plan
    membership_plan: str = Field(..., pattern=r'^(1year|3year|5year)$')
    membership_amount: int
    membership_base_price: int
    membership_gst_amount: int
    membership_duration_months: int
    
    # Account creation
    account_email: EmailStr
    account_password: str = Field(..., min_length=8)
    
    # Declaration
    declaration_accepted: bool
    declaration_timestamp: str


class SocietyRegistrationResponse(BaseModel):
    """Society registration response"""
    success: bool
    message: str
    society_id: Optional[int] = None
    user_id: Optional[int] = None
    membership_id: Optional[int] = None
    invoice_id: Optional[int] = None


# ============ MEMBER REGISTRATION ============

class NewSocietyData(BaseModel):
    """New society data for member registration"""
    name: str
    registration_number: str
    email: Optional[EmailStr] = None
    contact: Optional[str] = None
    address: Optional[str] = None
    total_members: Optional[int] = 0
    total_flats: Optional[int] = 0
    total_shops: Optional[int] = 0
    total_garages: Optional[int] = 0


class MemberRegistrationRequest(BaseModel):
    """Member registration request - ALL members must be connected to a society"""
    # Member category - All members are society members
    member_category: str = Field(default="society_member", pattern=r'^society_member$')
    
    # Personal details
    full_name: str = Field(..., min_length=3, max_length=255)
    email: EmailStr
    mobile: str = Field(..., pattern=r'^\d{10}$')
    address: str
    city: str
    state: str = "Maharashtra"
    pincode: str = Field(..., pattern=r'^\d{6}$')
    
    # Society details - MANDATORY for all members
    society_option: str = Field(..., pattern=r'^(select_existing|create_new)$')
    existing_society_id: Optional[int] = None
    new_society: Optional[NewSocietyData] = None
    
    # Designation - Required for all members
    designation: str = Field(..., min_length=1)
    
    # Membership plan
    membership_plan: str = Field(..., pattern=r'^(1year|3year|5year)$')
    membership_amount: int
    membership_base_price: int
    membership_gst_amount: int
    membership_duration_months: int
    
    # Account
    password: str = Field(..., min_length=8)
    
    # Declaration
    declaration_accepted: bool
    declaration_timestamp: str


class MemberRegistrationResponse(BaseModel):
    """Member registration response"""
    success: bool
    message: str
    member_id: Optional[int] = None
    user_id: Optional[int] = None
    society_id: Optional[int] = None
    membership_id: Optional[int] = None
    invoice_id: Optional[int] = None


# ============ VENDOR REGISTRATION ============

class VendorBusinessData(BaseModel):
    """Vendor business details"""
    name: str
    type: str  # sole_proprietorship, partnership, private_limited, llp
    owner_name: str
    email: EmailStr
    phone: str = Field(..., pattern=r'^\d{10}$')
    alternate_phone: Optional[str] = None
    gst_number: Optional[str] = None
    pan_number: str
    address: str
    city: str
    state: str = "Maharashtra"
    pincode: str = Field(..., pattern=r'^\d{6}$')
    website: Optional[str] = None
    years_of_experience: int = Field(0, ge=0)
    number_of_employees: int = Field(0, ge=0)


class VendorServicesData(BaseModel):
    """Vendor services details"""
    categories: List[str]
    other_category: Optional[str] = None
    description: str
    service_areas: List[str]
    other_area: Optional[str] = None


class VendorDocumentsData(BaseModel):
    """Vendor documents"""
    has_business_license: bool = False
    has_insurance: bool = False
    has_trade_license: bool = False


class VendorContactPerson(BaseModel):
    """Contact person (if different from owner)"""
    name: Optional[str] = None
    phone: Optional[str] = None
    designation: Optional[str] = None


class VendorRegistrationRequest(BaseModel):
    """Vendor registration request"""
    # Business details
    business: VendorBusinessData
    
    # Services
    services: VendorServicesData
    
    # Documents
    documents: VendorDocumentsData
    
    # Contact person
    contact_person: Optional[VendorContactPerson] = None
    
    # Account
    account_email: EmailStr
    account_password: str = Field(..., min_length=8)
    
    # Declaration
    declaration_accepted: bool
    declaration_timestamp: str
    
    # Status (set by system)
    status: str = "pending_approval"


class VendorRegistrationResponse(BaseModel):
    """Vendor registration response"""
    success: bool
    message: str
    provider_id: Optional[int] = None
    user_id: Optional[int] = None
    status: str = "pending_approval"
