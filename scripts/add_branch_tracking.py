"""
Script to add branch_id to existing records
Run this after adding branch_id columns to tables
"""

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.member import Member
from app.models.booking import ServiceBooking
from app.models.consultation import Consultation
from app.models.invoice import Invoice
from app.models.branch import Branch

def determine_branch_for_member(city: str, user_id: int = None) -> int:
    """Determine branch based on city or user assignment"""
    db = SessionLocal()
    try:
        # Map cities to branches (customize based on your branch setup)
        city_to_branch = {
            'mumbai': 'MUMBAI',
            'thane': 'THANE',
            'pune': 'PUNE',
            'nashik': 'NASHIK',
            'nagpur': 'NAGPUR',
        }
        
        branch_code = city_to_branch.get(city.lower(), 'MUMBAI')  # Default to Mumbai
        
        branch = db.query(Branch).filter(Branch.code == branch_code).first()
        if branch:
            return branch.id
        
        # Fallback to first active branch
        branch = db.query(Branch).filter(Branch.is_active == True).first()
        return branch.id if branch else None
    finally:
        db.close()

def update_member_branches():
    """Update branch_id for members based on city"""
    db = SessionLocal()
    try:
        members = db.query(Member).filter(Member.branch_id == None).all()
        updated = 0
        
        for member in members:
            if member.city:
                branch_id = determine_branch_for_member(member.city, member.user_id)
                if branch_id:
                    member.branch_id = branch_id
                    updated += 1
        
        db.commit()
        print(f"Updated {updated} members with branch_id")
    except Exception as e:
        db.rollback()
        print(f"Error updating members: {e}")
    finally:
        db.close()

def update_booking_branches():
    """Update branch_id for bookings based on member's branch"""
    db = SessionLocal()
    try:
        bookings = db.query(ServiceBooking).filter(ServiceBooking.branch_id == None).all()
        updated = 0
        
        for booking in bookings:
            if booking.client_user_id:
                # Get member from user
                from app.models.user import User
                user = db.query(User).filter(User.id == booking.client_user_id).first()
                if user and user.member_profile:
                    member = user.member_profile
                    if member.branch_id:
                        booking.branch_id = member.branch_id
                        updated += 1
        
        db.commit()
        print(f"Updated {updated} bookings with branch_id")
    except Exception as e:
        db.rollback()
        print(f"Error updating bookings: {e}")
    finally:
        db.close()

def update_consultation_branches():
    """Update branch_id for consultations based on member's branch"""
    db = SessionLocal()
    try:
        consultations = db.query(Consultation).filter(Consultation.branch_id == None).all()
        updated = 0
        
        for consultation in consultations:
            if consultation.member_id:
                member = db.query(Member).filter(Member.id == consultation.member_id).first()
                if member and member.branch_id:
                    consultation.branch_id = member.branch_id
                    updated += 1
        
        db.commit()
        print(f"Updated {updated} consultations with branch_id")
    except Exception as e:
        db.rollback()
        print(f"Error updating consultations: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    print("Starting branch tracking update...")
    update_member_branches()
    update_booking_branches()
    update_consultation_branches()
    print("Branch tracking update complete!")
