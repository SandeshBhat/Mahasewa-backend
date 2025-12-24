"""
Script to import publications and documents from MahaSewa Website Data Drive
"""
import os
import sys
from pathlib import Path
from sqlalchemy.orm import Session
from decimal import Decimal
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.db.session import get_db
from app.models.content import Download
from app.services.s3_service import file_storage

# Paths to the data drive folders
BASE_DATA_DRIVE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "MahaSewa Website Data Drive"
)

# Use /tmp paths since files are copied there
PUBLICATIONS_PATH = "/tmp/mahasewa-publications"
MAGAZINES_PATH = "/tmp/mahasewa-magazines"
CIRCULARS_PATH = "/tmp/mahasewa-circulars"


def get_file_size(file_path: str) -> int:
    """Get file size in bytes"""
    try:
        return os.path.getsize(file_path)
    except:
        return 0


def get_file_type(filename: str) -> str:
    """Determine file type from extension"""
    ext = Path(filename).suffix.lower().lstrip('.')
    if ext == 'pdf':
        return 'pdf'
    elif ext in ['doc', 'docx']:
        return 'document'
    elif ext in ['jpg', 'jpeg', 'png']:
        return 'image'
    else:
        return 'other'


def import_publications(db: Session, publications_path: str = PUBLICATIONS_PATH):
    """
    Import publication books and documents
    
    Args:
        db: Database session
        publications_path: Path to publications folder
    """
    if not os.path.exists(publications_path):
        print(f"Warning: Publications folder not found at: {publications_path}")
        return 0, 0, 0
    
    print(f"Scanning publications folder: {publications_path}")
    
    imported_count = 0
    skipped_count = 0
    error_count = 0
    
    # Process PDF files
    for root, dirs, files in os.walk(publications_path):
        for file in files:
            file_path = os.path.join(root, file)
            file_ext = Path(file).suffix.lower()
            
            # Only process PDFs and images
            if file_ext not in ['.pdf', '.jpg', '.jpeg', '.png']:
                continue
            
            # Skip if it's a cover image (look for corresponding PDF)
            if file_ext in ['.jpg', '.jpeg', '.png']:
                pdf_name = Path(file).stem + '.pdf'
                pdf_path = os.path.join(root, pdf_name)
                if os.path.exists(pdf_path):
                    # This is a cover image, skip it (we'll handle it when processing the PDF)
                    continue
            
            # Check if already imported
            existing = db.query(Download).filter(
                Download.file_url.like(f"%{file}%")
            ).first()
            
            if existing:
                print(f"Skipping (already exists): {file}")
                skipped_count += 1
                continue
            
            try:
                # Determine category
                folder_name = os.path.basename(root)
                if 'book index' in folder_name.lower():
                    category = 'books'
                    subcategory = 'index'
                else:
                    category = 'publications'
                    subcategory = None
                
                # Check for cover image
                cover_image_url = None
                cover_name = Path(file).stem + '.jpg'
                cover_path = os.path.join(root, cover_name)
                if not os.path.exists(cover_path):
                    # Try other extensions
                    for ext in ['.png', '.jpeg']:
                        cover_path = os.path.join(root, Path(file).stem + ext)
                        if os.path.exists(cover_path):
                            cover_name = Path(cover_path).name
                            break
                
                if os.path.exists(cover_path):
                    # Upload cover image
                    cover_storage_path = f"publications/covers/{cover_name}"
                    cover_url = file_storage.upload_file_from_path(
                        source_path=cover_path,
                        file_path=cover_storage_path,
                        subdirectory='downloads'
                    )
                    if cover_url:
                        cover_image_url = cover_url
                
                # Upload main file
                storage_filename = f"publications/{file}"
                url = file_storage.upload_file_from_path(
                    source_path=file_path,
                    file_path=storage_filename,
                    subdirectory='downloads'
                )
                
                if not url:
                    print(f"Error uploading: {file}")
                    error_count += 1
                    continue
                
                # Extract title from filename
                title = Path(file).stem.replace('_', ' ').replace('-', ' ').title()
                
                # Create download entry
                download = Download(
                    title=title,
                    description=f"Publication: {title}",
                    file_url=url,
                    file_type=get_file_type(file),
                    file_size=get_file_size(file_path),
                    category=category,
                    subcategory=subcategory,
                    cover_image_url=cover_image_url,
                    is_free=False,  # Publications may be paid
                    price=Decimal('0'),  # Set price as needed
                    access_level='member',  # Typically for members
                    requires_membership=True,
                    is_active=True,
                    download_count=0,
                    purchase_count=0,
                    total_revenue=Decimal('0')
                )
                
                db.add(download)
                db.commit()
                
                print(f"✓ Imported: {file} -> {url}")
                imported_count += 1
                
            except Exception as e:
                print(f"Error importing {file}: {e}")
                db.rollback()
                error_count += 1
    
    return imported_count, skipped_count, error_count


def import_magazines(db: Session, magazines_path: str = MAGAZINES_PATH):
    """
    Import magazine PDFs
    
    Args:
        db: Database session
        magazines_path: Path to magazines folder
    """
    if not os.path.exists(magazines_path):
        print(f"Warning: Magazines folder not found at: {magazines_path}")
        return 0, 0, 0, 0, 0
    
    print(f"Scanning magazines folder: {magazines_path}")
    
    imported_count = 0
    skipped_count = 0
    error_count = 0
    
    for file in os.listdir(magazines_path):
        file_path = os.path.join(magazines_path, file)
        
        if not os.path.isfile(file_path):
            continue
        
        file_ext = Path(file).suffix.lower()
        if file_ext != '.pdf':
            continue
        
        # Check if already imported
        existing = db.query(Download).filter(
            Download.file_url.like(f"%{file}%")
        ).first()
        
        if existing:
            print(f"Skipping (already exists): {file}")
            skipped_count += 1
            continue
        
        try:
            # Check for cover image
            cover_image_url = None
            cover_name = Path(file).stem + '.jpg'
            cover_path = os.path.join(magazines_path, cover_name)
            if os.path.exists(cover_path):
                cover_storage_path = f"magazines/covers/{cover_name}"
                cover_url = file_storage.upload_file_from_path(
                    source_path=cover_path,
                    file_path=cover_storage_path,
                    subdirectory='downloads'
                )
                if cover_url:
                    cover_image_url = cover_url
            
            # Upload PDF
            storage_filename = f"magazines/{file}"
            url = file_storage.upload_file_from_path(
                source_path=file_path,
                file_path=storage_filename,
                subdirectory='downloads'
            )
            
            if not url:
                print(f"Error uploading: {file}")
                error_count += 1
                continue
            
            # Extract month/year from filename
            title = Path(file).stem.replace('_', ' ').replace('-', ' ').title()
            
            # Create download entry
            download = Download(
                title=f"MahaSeWA Magazine - {title}",
                description=f"Monthly magazine: {title}",
                file_url=url,
                file_type='pdf',
                file_size=get_file_size(file_path),
                category='magazines',
                subcategory='monthly',
                cover_image_url=cover_image_url,
                is_free=True,  # Magazines might be free for members
                price=Decimal('0'),
                access_level='member',
                requires_membership=True,
                is_active=True,
                download_count=0,
                purchase_count=0,
                total_revenue=Decimal('0')
            )
            
            db.add(download)
            db.commit()
            
            print(f"✓ Imported: {file} -> {url}")
            imported_count += 1
            
        except Exception as e:
            print(f"Error importing {file}: {e}")
            db.rollback()
            error_count += 1
    
    return imported_count, skipped_count, error_count


def import_circulars(db: Session, circulars_path: str = CIRCULARS_PATH):
    """
    Import circular documents
    
    Args:
        db: Database session
        circulars_path: Path to circulars folder
    """
    if not os.path.exists(circulars_path):
        print(f"Warning: Circulars folder not found at: {circulars_path}")
        return 0, 0, 0
    
    print(f"Scanning circulars folder: {circulars_path}")
    print("Note: This folder contains many files. Processing may take time...")
    
    imported_count = 0
    skipped_count = 0
    error_count = 0
    
    # Limit to first 100 files to avoid overwhelming the system
    # Remove this limit if you want to import all
    file_limit = 100
    processed = 0
    
    for root, dirs, files in os.walk(circulars_path):
        for file in files:
            if processed >= file_limit:
                print(f"Reached limit of {file_limit} files. Stopping.")
                break
            
            file_path = os.path.join(root, file)
            file_ext = Path(file).suffix.lower()
            
            if file_ext not in ['.pdf', '.doc', '.docx']:
                continue
            
            # Check if already imported
            existing = db.query(Download).filter(
                Download.file_url.like(f"%{file}%")
            ).first()
            
            if existing:
                skipped_count += 1
                continue
            
            try:
                # Upload file
                relative_path = os.path.relpath(file_path, circulars_path)
                storage_filename = f"circulars/{relative_path}"
                
                url = file_storage.upload_file_from_path(
                    source_path=file_path,
                    file_path=storage_filename,
                    subdirectory='downloads'
                )
                
                if not url:
                    error_count += 1
                    continue
                
                # Create download entry
                title = Path(file).stem.replace('_', ' ').replace('-', ' ').title()
                
                download = Download(
                    title=title,
                    description=f"Circular: {title}",
                    file_url=url,
                    file_type=get_file_type(file),
                    file_size=get_file_size(file_path),
                    category='circulars',
                    subcategory=None,
                    is_free=True,
                    price=Decimal('0'),
                    access_level='public',
                    requires_membership=False,
                    is_active=True,
                    download_count=0,
                    purchase_count=0,
                    total_revenue=Decimal('0')
                )
                
                db.add(download)
                db.commit()
                
                imported_count += 1
                processed += 1
                
                if processed % 10 == 0:
                    print(f"Processed {processed} files...")
                
            except Exception as e:
                print(f"Error importing {file}: {e}")
                db.rollback()
                error_count += 1
        
        if processed >= file_limit:
            break
    
    return imported_count, skipped_count, error_count


if __name__ == "__main__":
    print("MahaSeWA Publications Import Script")
    print("="*50)
    
    # Get database session
    db = next(get_db())
    
    try:
        total_imported = 0
        total_skipped = 0
        total_errors = 0
        
        # Import publications
        print("\n1. Importing Publications...")
        imp, skp, err = import_publications(db)
        total_imported += imp
        total_skipped += skp
        total_errors += err
        
        # Import magazines
        print("\n2. Importing Magazines...")
        imp, skp, err = import_magazines(db)
        total_imported += imp
        total_skipped += skp
        total_errors += err
        
        # Import circulars (limited)
        print("\n3. Importing Circulars (limited to 100 files)...")
        imp, skp, err = import_circulars(db)
        total_imported += imp
        total_skipped += skp
        total_errors += err
        
        print("\n" + "="*50)
        print(f"Import complete!")
        print(f"  Total Imported: {total_imported}")
        print(f"  Total Skipped: {total_skipped}")
        print(f"  Total Errors: {total_errors}")
        print("="*50)
        
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

