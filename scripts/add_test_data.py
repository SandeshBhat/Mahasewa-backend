"""
Script to add test data for MahaSeWA platform
Run with: python -m backend.scripts.add_test_data
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine
from app.models.society import Society
from app.models.provider import ServiceProvider, VerificationStatus
from app.models.member import Member
from app.models.user import User, UserRole
from app.models.content import Event, BlogPost
from datetime import datetime, timedelta
import random

def create_test_societies(db: Session):
    """Create test housing societies"""
    societies_data = [
        {
            "name": "Green Valley Housing Society",
            "registration_number": "MH/HS/2020/001",
            "address": "Green Valley, Sector 5",
            "city": "Mumbai",
            "state": "Maharashtra",
            "pincode": "400001",
            "phone": "+91-22-12345678",
            "email": "greenvalley@example.com",
            "total_units": 120,
            "total_members": 95,
            "year_established": 2020,
            "is_verified": True,
            "is_active": True
        },
        {
            "name": "Sunshine Apartments",
            "registration_number": "MH/HS/2019/045",
            "address": "Sunshine Complex, Andheri West",
            "city": "Mumbai",
            "state": "Maharashtra",
            "pincode": "400053",
            "phone": "+91-22-23456789",
            "email": "sunshine@example.com",
            "total_units": 80,
            "total_members": 75,
            "year_established": 2019,
            "is_verified": True,
            "is_active": True
        },
        {
            "name": "Royal Heights Society",
            "registration_number": "MH/HS/2021/089",
            "address": "Royal Heights, Powai",
            "city": "Mumbai",
            "state": "Maharashtra",
            "pincode": "400076",
            "phone": "+91-22-34567890",
            "email": "royalheights@example.com",
            "total_units": 200,
            "total_members": 180,
            "year_established": 2021,
            "is_verified": False,
            "is_active": True
        },
        {
            "name": "Prestige Gardens",
            "registration_number": "MH/HS/2018/123",
            "address": "Prestige Gardens, Bandra",
            "city": "Mumbai",
            "state": "Maharashtra",
            "pincode": "400050",
            "phone": "+91-22-45678901",
            "email": "prestige@example.com",
            "total_units": 150,
            "total_members": 140,
            "year_established": 2018,
            "is_verified": True,
            "is_active": True
        },
        {
            "name": "Harmony Residency",
            "registration_number": "MH/HS/2022/156",
            "address": "Harmony Residency, Thane",
            "city": "Thane",
            "state": "Maharashtra",
            "pincode": "400601",
            "phone": "+91-22-56789012",
            "email": "harmony@example.com",
            "total_units": 100,
            "total_members": 85,
            "year_established": 2022,
            "is_verified": False,
            "is_active": True
        },
        {
            "name": "Elite Towers",
            "registration_number": "MH/HS/2017/234",
            "address": "Elite Towers, Vashi",
            "city": "Navi Mumbai",
            "state": "Maharashtra",
            "pincode": "400703",
            "phone": "+91-22-67890123",
            "email": "elite@example.com",
            "total_units": 180,
            "total_members": 170,
            "year_established": 2017,
            "is_verified": True,
            "is_active": True
        }
    ]
    
    created = 0
    for data in societies_data:
        # Check if society already exists
        existing = db.query(Society).filter(
            Society.registration_number == data["registration_number"]
        ).first()
        
        if not existing:
            society = Society(**data)
            db.add(society)
            created += 1
        else:
            # Update existing
            for key, value in data.items():
                setattr(existing, key, value)
            created += 1
    
    db.commit()
    print(f"✅ Created/Updated {created} societies")
    return created


def create_test_providers(db: Session):
    """Create test service providers"""
    providers_data = [
        {
            "business_name": "Mumbai Plumbing Services",
            "contact_name": "Rajesh Kumar",
            "email": "rajesh@mumbaiplumbing.com",
            "phone": "+91-9876543210",
            "city": "Mumbai",
            "state": "Maharashtra",
            "service_categories": ["plumbing", "maintenance"],
            "verification_status": VerificationStatus.VERIFIED,
            "is_active": True
        },
        {
            "business_name": "Electrical Solutions Pro",
            "contact_name": "Priya Sharma",
            "email": "priya@electricalpro.com",
            "phone": "+91-9876543211",
            "city": "Mumbai",
            "state": "Maharashtra",
            "service_categories": ["electrical", "repairs"],
            "verification_status": VerificationStatus.VERIFIED,
            "is_active": True
        },
        {
            "business_name": "Legal Advisors & Associates",
            "contact_name": "Amit Patel",
            "email": "amit@legaladvisors.com",
            "phone": "+91-9876543212",
            "city": "Mumbai",
            "state": "Maharashtra",
            "service_categories": ["legal", "consultation"],
            "verification_status": VerificationStatus.PENDING,
            "is_active": True
        },
        {
            "business_name": "Security Services Mumbai",
            "contact_name": "Vikram Singh",
            "email": "vikram@securitymumbai.com",
            "phone": "+91-9876543213",
            "city": "Mumbai",
            "state": "Maharashtra",
            "service_categories": ["security", "surveillance"],
            "verification_status": VerificationStatus.VERIFIED,
            "is_active": True
        },
        {
            "business_name": "Garden Maintenance Experts",
            "contact_name": "Sunita Desai",
            "email": "sunita@gardenexperts.com",
            "phone": "+91-9876543214",
            "city": "Thane",
            "state": "Maharashtra",
            "service_categories": ["landscaping", "maintenance"],
            "verification_status": VerificationStatus.PENDING,
            "is_active": True
        }
    ]
    
    created = 0
    for data in providers_data:
        existing = db.query(ServiceProvider).filter(
            ServiceProvider.email == data["email"]
        ).first()
        
        if not existing:
            provider = ServiceProvider(**data)
            db.add(provider)
            created += 1
        else:
            for key, value in data.items():
                setattr(existing, key, value)
            created += 1
    
    db.commit()
    print(f"✅ Created/Updated {created} service providers")
    return created


def create_test_events(db: Session):
    """Create test events"""
    events_data = [
        {
            "title": "Annual General Meeting 2025",
            "description": "Annual general meeting for all society members",
            "event_date": datetime.now() + timedelta(days=30),
            "location": "Society Clubhouse",
            "city": "Mumbai",
            "registration_required": True,
            "max_attendees": 200,
            "is_published": True
        },
        {
            "title": "Festival Celebration - Diwali",
            "description": "Community Diwali celebration with cultural programs",
            "event_date": datetime.now() + timedelta(days=45),
            "location": "Society Ground",
            "city": "Mumbai",
            "registration_required": False,
            "max_attendees": 500,
            "is_published": True
        },
        {
            "title": "Legal Awareness Workshop",
            "description": "Workshop on housing society legal rights and compliance",
            "event_date": datetime.now() + timedelta(days=60),
            "location": "Community Hall",
            "city": "Mumbai",
            "registration_required": True,
            "max_attendees": 100,
            "is_published": True
        },
        {
            "title": "Maintenance Training Session",
            "description": "Training session on building maintenance and safety",
            "event_date": datetime.now() + timedelta(days=15),
            "location": "Society Office",
            "city": "Mumbai",
            "registration_required": True,
            "max_attendees": 50,
            "is_published": True
        }
    ]
    
    created = 0
    for data in events_data:
        event = Event(**data)
        db.add(event)
        created += 1
    
    db.commit()
    print(f"✅ Created {created} events")
    return created


def main():
    """Main function to add all test data"""
    db = SessionLocal()
    
    try:
        print("🚀 Starting test data creation...")
        print("-" * 50)
        
        societies_count = create_test_societies(db)
        providers_count = create_test_providers(db)
        events_count = create_test_events(db)
        
        print("-" * 50)
        print(f"✅ Test data creation complete!")
        print(f"   - Societies: {societies_count}")
        print(f"   - Service Providers: {providers_count}")
        print(f"   - Events: {events_count}")
        
    except Exception as e:
        print(f"❌ Error creating test data: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
