"""Create initial admin user"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.user import User, UserRole
from app.utils.auth import get_password_hash

def create_admin_user():
    """Create or reset the admin user for MahaSeWA"""
    db: Session = SessionLocal()
    
    try:
        # Check if admin exists
        existing_admin = db.query(User).filter(
            User.email == "admin@mahasewa.org"
        ).first()
        
        if existing_admin:
            print("⚠️  Admin user already exists!")
            print(f"   Email: {existing_admin.email}")
            print(f"   Role: {existing_admin.role}")
            print(f"   Active: {existing_admin.is_active}")
            print(f"   Verified: {existing_admin.is_verified}")
            print("\n🔄 Resetting password to: Admin@123")
            
            # Reset password
            existing_admin.password_hash = get_password_hash("Admin@123")
            existing_admin.is_active = True
            existing_admin.is_verified = True
            db.commit()
            db.refresh(existing_admin)
            
            print("✅ Admin password reset successfully!")
            print(f"   Email: {existing_admin.email}")
            print(f"   Password: Admin@123")
            print(f"   Role: {existing_admin.role}")
            print(f"   ID: {existing_admin.id}")
            print("\n🔐 Login Credentials:")
            print("   Email: admin@mahasewa.org")
            print("   Password: Admin@123")
            return
        
        # Create admin user
        hashed_password = get_password_hash("Admin@123")
        
        admin = User(
            email="admin@mahasewa.org",
            password_hash=hashed_password,
            full_name="MahaSeWA Administrator",
            role=UserRole.SUPER_ADMIN,
            is_active=True,
            is_verified=True,
            phone="9876543210"
        )
        
        db.add(admin)
        db.commit()
        db.refresh(admin)
        
        print("✅ Admin user created successfully!")
        print(f"   Email: {admin.email}")
        print(f"   Password: admin123")
        print(f"   Role: {admin.role}")
        print(f"   ID: {admin.id}")
        print("\n🔐 Login Credentials:")
        print("   Email: admin@mahasewa.org")
        print("   Password: admin123")
        print("\n🌐 Login URL:")
        print("   https://mahasewa.vercel.app/login")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error creating admin user: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    print("🚀 Creating MahaSeWA Admin User...")
    print("=" * 50)
    create_admin_user()
