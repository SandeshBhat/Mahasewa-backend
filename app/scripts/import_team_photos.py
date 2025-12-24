"""
Script to import team photos for Board of Directors
"""
import os
import sys
from pathlib import Path
from sqlalchemy.orm import Session

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.db.session import get_db
from app.models.content import Gallery
from app.services.s3_service import file_storage

# Team members mapping
TEAM_MEMBERS = [
    ("Ramesh-Prabhu.jpg", "CA. Ramesh S. Prabhu", "Expert Mentor"),
    ("Sahana-Prabhu.jpg", "Mrs. Sahana S. Prabhu", "Managing Director"),
    ("viswanathan-vaidyanathan.png", "Mr. V. Viswanathan", "Expert Director"),
    ("Naresh Pai.png", "Adv. Naresh Pai", "Panel Consultant")
]


def import_team_photos(db: Session, photos_path: str = "/tmp/mahasewa-team-photos"):
    """
    Import team photos for Board of Directors
    
    Args:
        db: Database session
        photos_path: Path to team photos folder
    """
    if not os.path.exists(photos_path):
        print(f"Error: Team photos folder not found at: {photos_path}")
        return
    
    print(f"Scanning team photos folder: {photos_path}")
    
    imported_count = 0
    skipped_count = 0
    error_count = 0
    
    for filename, name, role in TEAM_MEMBERS:
        file_path = os.path.join(photos_path, filename)
        
        if not os.path.exists(file_path):
            print(f"Warning: File not found: {file_path}")
            error_count += 1
            continue
        
        # Check if already imported
        existing = db.query(Gallery).filter(
            Gallery.title == name,
            Gallery.category == "team"
        ).first()
        
        if existing:
            print(f"Skipping (already exists): {name}")
            skipped_count += 1
            continue
        
        try:
            # Upload file to storage
            storage_filename = f"team/{filename}"
            url = file_storage.upload_file_from_path(
                source_path=file_path,
                file_path=storage_filename,
                subdirectory='gallery'
            )
            
            if not url:
                print(f"Error uploading: {filename}")
                error_count += 1
                continue
            
            # Create gallery entry
            gallery_item = Gallery(
                title=name,
                description=f"{role} - Board of Directors",
                image_url=url,
                thumbnail_url=url,
                category="team",
                album="Board of Directors",
                tags=["team", "leaders", "board"],
                is_featured=True,  # Featured so they show prominently
                is_active=True,
                display_order=0,
                view_count=0
            )
            
            db.add(gallery_item)
            db.commit()
            
            print(f"✓ Imported: {name} -> {url}")
            imported_count += 1
            
        except Exception as e:
            print(f"Error importing {filename}: {e}")
            db.rollback()
            error_count += 1
    
    print("\n" + "="*50)
    print(f"Import complete!")
    print(f"  Imported: {imported_count}")
    print(f"  Skipped: {skipped_count}")
    print(f"  Errors: {error_count}")
    print("="*50)


if __name__ == "__main__":
    print("MahaSeWA Team Photos Import Script")
    print("="*50)
    
    # Get database session
    db = next(get_db())
    
    try:
        # Check if custom path provided
        if len(sys.argv) > 1:
            custom_path = sys.argv[1]
            if os.path.exists(custom_path):
                import_team_photos(db, custom_path)
            else:
                print(f"Error: Path not found: {custom_path}")
        else:
            import_team_photos(db)
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

