"""Import societies from CSV file"""
import csv
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.society import Society


def clean_field(value: str) -> str:
    """Clean CSV field value"""
    if not value or value == ",,":
        return ""
    return value.strip().strip(',').strip('"')


def import_societies_from_csv(csv_path: str):
    """Import societies from CSV file"""
    db: Session = SessionLocal()
    
    try:
        imported_count = 0
        skipped_count = 0
        
        with open(csv_path, 'r', encoding='utf-8') as file:
            # Skip first line (headers with line breaks)
            next(file)
            
            reader = csv.reader(file)
            
            for row in reader:
                if len(row) < 12:
                    skipped_count += 1
                    continue
                
                try:
                    sr_no = row[0]
                    membership_no = clean_field(row[1])
                    society_type = clean_field(row[3])
                    society_name = clean_field(row[4])
                    address_1 = clean_field(row[5])
                    address_2 = clean_field(row[6])
                    city = clean_field(row[7])
                    state = clean_field(row[8])
                    pincode = clean_field(row[9])
                    mobile = clean_field(row[10])
                    landline = clean_field(row[11])
                    email = clean_field(row[12]) if len(row) > 12 else ""
                    gst_no = clean_field(row[13]) if len(row) > 13 else ""
                    reg_no = clean_field(row[14]) if len(row) > 14 else ""
                    total_members = clean_field(row[15]) if len(row) > 15 else "0"
                    
                    # Skip if not a society or missing name
                    if society_type != "SOCIETY" or not society_name:
                        skipped_count += 1
                        continue
                    
                    # Check if already exists by membership number
                    if membership_no:
                        existing = db.query(Society).filter(
                            Society.documents['membership_no'].astext == membership_no
                        ).first()
                        if existing:
                            skipped_count += 1
                            continue
                    
                    # Combine address
                    address_parts = [address_1, address_2]
                    full_address = ", ".join([p for p in address_parts if p])
                    
                    # Create society
                    society = Society(
                        name=society_name,
                        registration_number=reg_no or membership_no or f"IMPORT-{sr_no}",
                        address=full_address or "Address not provided",
                        city=city or "Mumbai",
                        state=state or "Maharashtra",
                        pincode=pincode,
                        phone=mobile or landline,
                        email=email if email and '@' in email else None,
                        total_members=int(total_members) if total_members.isdigit() else 0,
                        is_verified=True,  # Pre-existing societies are verified
                        is_active=True,
                        documents={
                            "membership_no": membership_no,
                            "gst_no": gst_no,
                            "mobile": mobile,
                            "landline": landline,
                            "imported_from_csv": True,
                            "sr_no": sr_no
                        }
                    )
                    
                    db.add(society)
                    imported_count += 1
                    
                    # Commit in batches of 100
                    if imported_count % 100 == 0:
                        db.commit()
                        print(f"Imported {imported_count} societies...")
                
                except Exception as e:
                    print(f"Error importing row {sr_no}: {str(e)}")
                    skipped_count += 1
                    continue
        
        # Final commit
        db.commit()
        
        print(f"\n✅ Import Complete!")
        print(f"   Imported: {imported_count} societies")
        print(f"   Skipped: {skipped_count} records")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Import failed: {str(e)}")
    finally:
        db.close()


if __name__ == "__main__":
    csv_file = "../../ Society.csv"  # Adjust path as needed
    
    print("🚀 Starting CSV import...")
    print(f"📁 Reading from: {csv_file}")
    
    import_societies_from_csv(csv_file)
