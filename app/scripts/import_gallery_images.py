"""
Script to import gallery images from MahaSewa Website Data Drive
"""
import os
import sys
from pathlib import Path
from sqlalchemy.orm import Session
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.db.session import get_db
from app.models.content import Gallery
from app.services.s3_service import file_storage

# Path to the MahaSewa Website Data Drive folder
# Try multiple possible locations
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
project_root = os.path.dirname(backend_dir)

# Try relative path from backend
DATA_DRIVE_PATH = os.path.join(project_root, "MahaSewa Website Data Drive", "MahaSewa Photo Gallery")

# If not found, try absolute path
if not os.path.exists(DATA_DRIVE_PATH):
    # Try from project root directly
    alt_path = os.path.join(os.path.dirname(project_root), "MahaSewa Website Data Drive", "MahaSewa Photo Gallery")
    if os.path.exists(alt_path):
        DATA_DRIVE_PATH = alt_path
    else:
        # Default to project root location
        DATA_DRIVE_PATH = os.path.join(project_root, "MahaSewa Website Data Drive", "MahaSewa Photo Gallery")


def import_gallery_images(db: Session, data_drive_path: str = DATA_DRIVE_PATH):
    """
    Import gallery images from the data drive folder
    
    Args:
        db: Database session
        data_drive_path: Path to the gallery folder
    """
    if not os.path.exists(data_drive_path):
        print(f"Error: Gallery folder not found at: {data_drive_path}")
        print("Please update DATA_DRIVE_PATH in the script to point to the correct location.")
        return
    
    print(f"Scanning gallery folder: {data_drive_path}")
    
    # Supported image extensions
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    
    imported_count = 0
    skipped_count = 0
    error_count = 0
    
    # Walk through the directory
    for root, dirs, files in os.walk(data_drive_path):
        # Determine category from folder name
        relative_path = os.path.relpath(root, data_drive_path)
        if relative_path == '.':
            category = 'general'
            album = None
        else:
            # Use folder name as category/album
            folder_name = os.path.basename(root)
            if folder_name.upper() == 'RSP':
                category = 'rsp'
                album = 'RSP'
            else:
                category = folder_name.lower().replace(' ', '_')
                album = folder_name
        
        for file in files:
            file_path = os.path.join(root, file)
            file_ext = Path(file).suffix.lower()
            
            # Skip non-image files
            if file_ext not in image_extensions:
                continue
            
            # Check if already imported (by filename)
            existing = db.query(Gallery).filter(
                Gallery.image_url.like(f"%{file}%")
            ).first()
            
            if existing:
                print(f"Skipping (already exists): {file}")
                skipped_count += 1
                continue
            
            try:
                # Upload file to storage
                relative_file_path = os.path.relpath(file_path, data_drive_path)
                # Create a clean filename for storage
                storage_filename = f"{category}/{file}" if category != 'general' else file
                
                url = file_storage.upload_file_from_path(
                    source_path=file_path,
                    file_path=storage_filename,
                    subdirectory='gallery'
                )
                
                if not url:
                    print(f"Error uploading: {file}")
                    error_count += 1
                    continue
                
                # Create gallery entry
                gallery_item = Gallery(
                    title=Path(file).stem.replace('_', ' ').replace('-', ' ').title(),
                    description=f"Imported from {relative_path}" if relative_path != '.' else None,
                    image_url=url,
                    thumbnail_url=url,  # Can be optimized later
                    category=category,
                    album=album,
                    tags=[category] if category != 'general' else [],
                    is_featured=False,
                    is_active=True,
                    display_order=0,
                    view_count=0
                )
                
                db.add(gallery_item)
                db.commit()
                
                print(f"✓ Imported: {file} -> {url}")
                imported_count += 1
                
            except Exception as e:
                print(f"Error importing {file}: {e}")
                db.rollback()
                error_count += 1
    
    print("\n" + "="*50)
    print(f"Import complete!")
    print(f"  Imported: {imported_count}")
    print(f"  Skipped: {skipped_count}")
    print(f"  Errors: {error_count}")
    print("="*50)


if __name__ == "__main__":
    print("MahaSeWA Gallery Image Import Script")
    print("="*50)
    
    # Get database session
    db = next(get_db())
    
    try:
        # Check if custom path provided
        if len(sys.argv) > 1:
            custom_path = sys.argv[1]
            if os.path.exists(custom_path):
                import_gallery_images(db, custom_path)
            else:
                print(f"Error: Path not found: {custom_path}")
        else:
            import_gallery_images(db)
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

