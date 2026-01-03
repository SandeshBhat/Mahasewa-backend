"""Analyze CSV file and compare with database"""
import csv
import sys
from pathlib import Path
from collections import defaultdict

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.society import Society


def analyze_csv(csv_path: str):
    """Analyze CSV file structure and data"""
    print("=" * 80)
    print("CSV FILE ANALYSIS")
    print("=" * 80)
    
    csv_stats = {
        'total_rows': 0,
        'societies': 0,
        'individuals': 0,
        'invalid': 0,
        'with_email': 0,
        'with_phone': 0,
        'with_registration': 0,
        'with_gst': 0,
        'with_members': 0,
        'cities': defaultdict(int),
        'missing_fields': defaultdict(int),
    }
    
    with open(csv_path, 'r', encoding='utf-8') as file:
        # Skip header
        next(file)
        
        reader = csv.reader(file)
        
        for row in reader:
            csv_stats['total_rows'] += 1
            
            if len(row) < 12:
                csv_stats['invalid'] += 1
                continue
            
            try:
                society_type = row[3].strip().strip('"').upper() if len(row) > 3 else ""
                society_name = row[4].strip().strip('"') if len(row) > 4 else ""
                email = row[12].strip().strip('"') if len(row) > 12 else ""
                mobile = row[10].strip().strip('"') if len(row) > 10 else ""
                landline = row[11].strip().strip('"') if len(row) > 11 else ""
                reg_no = row[14].strip().strip('"') if len(row) > 14 else ""
                gst_no = row[13].strip().strip('"') if len(row) > 13 else ""
                total_members = row[15].strip().strip('"') if len(row) > 15 else "0"
                city = row[7].strip().strip('"') if len(row) > 7 else ""
                
                if society_type == "SOCIETY" and society_name:
                    csv_stats['societies'] += 1
                    
                    if email and '@' in email:
                        csv_stats['with_email'] += 1
                    
                    if mobile or landline:
                        csv_stats['with_phone'] += 1
                    
                    if reg_no:
                        csv_stats['with_registration'] += 1
                    
                    if gst_no:
                        csv_stats['with_gst'] += 1
                    
                    if total_members.isdigit() and int(total_members) > 0:
                        csv_stats['with_members'] += 1
                    
                    if city:
                        csv_stats['cities'][city] += 1
                    
                    # Check missing fields
                    if not society_name:
                        csv_stats['missing_fields']['name'] += 1
                    if not city:
                        csv_stats['missing_fields']['city'] += 1
                    if not email or '@' not in email:
                        csv_stats['missing_fields']['email'] += 1
                    if not mobile and not landline:
                        csv_stats['missing_fields']['phone'] += 1
                        
            except Exception as e:
                csv_stats['invalid'] += 1
                continue
    
    print(f"\n📊 CSV Statistics:")
    print(f"   Total Rows: {csv_stats['total_rows']}")
    print(f"   Societies: {csv_stats['societies']}")
    print(f"   Individuals: {csv_stats['individuals']}")
    print(f"   Invalid Rows: {csv_stats['invalid']}")
    print(f"\n📋 Data Quality:")
    print(f"   With Email: {csv_stats['with_email']} ({csv_stats['with_email']/csv_stats['societies']*100:.1f}%)")
    print(f"   With Phone: {csv_stats['with_phone']} ({csv_stats['with_phone']/csv_stats['societies']*100:.1f}%)")
    print(f"   With Registration No: {csv_stats['with_registration']} ({csv_stats['with_registration']/csv_stats['societies']*100:.1f}%)")
    print(f"   With GST No: {csv_stats['with_gst']} ({csv_stats['with_gst']/csv_stats['societies']*100:.1f}%)")
    print(f"   With Member Count: {csv_stats['with_members']} ({csv_stats['with_members']/csv_stats['societies']*100:.1f}%)")
    
    print(f"\n🏙️ Top 10 Cities:")
    for city, count in sorted(csv_stats['cities'].items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"   {city}: {count}")
    
    print(f"\n⚠️ Missing Fields:")
    for field, count in csv_stats['missing_fields'].items():
        print(f"   {field}: {count}")
    
    return csv_stats


def analyze_database():
    """Analyze database societies"""
    print("\n" + "=" * 80)
    print("DATABASE ANALYSIS")
    print("=" * 80)
    
    db: Session = SessionLocal()
    
    try:
        total = db.query(Society).count()
        verified = db.query(Society).filter(Society.is_verified == True).count()
        active = db.query(Society).filter(Society.is_active == True).count()
        
        with_email = db.query(Society).filter(Society.email.isnot(None), Society.email != '').count()
        with_phone = db.query(Society).filter(Society.phone.isnot(None), Society.phone != '').count()
        with_registration = db.query(Society).filter(Society.registration_number.isnot(None), Society.registration_number != '').count()
        with_members = db.query(Society).filter(Society.total_members > 0).count()
        imported_from_csv = db.query(Society).filter(Society.documents['imported_from_csv'].astext == 'true').count()
        
        # City distribution
        from sqlalchemy import func
        city_counts = db.query(
            Society.city,
            func.count(Society.id).label('count')
        ).group_by(Society.city).order_by(func.count(Society.id).desc()).limit(10).all()
        
        print(f"\n📊 Database Statistics:")
        print(f"   Total Societies: {total}")
        print(f"   Verified: {verified} ({verified/total*100:.1f}%)")
        print(f"   Active: {active} ({active/total*100:.1f}%)")
        print(f"   Imported from CSV: {imported_from_csv} ({imported_from_csv/total*100:.1f}%)")
        
        print(f"\n📋 Data Quality:")
        print(f"   With Email: {with_email} ({with_email/total*100:.1f}%)")
        print(f"   With Phone: {with_phone} ({with_phone/total*100:.1f}%)")
        print(f"   With Registration No: {with_registration} ({with_registration/total*100:.1f}%)")
        print(f"   With Member Count: {with_members} ({with_members/total*100:.1f}%)")
        
        print(f"\n🏙️ Top 10 Cities:")
        for city, count in city_counts:
            print(f"   {city}: {count}")
        
        # Sample societies
        print(f"\n📝 Sample Societies (first 5):")
        samples = db.query(Society).limit(5).all()
        for s in samples:
            print(f"   - {s.name} ({s.city}) - Email: {'Yes' if s.email else 'No'}, Phone: {'Yes' if s.phone else 'No'}")
        
    finally:
        db.close()


def compare_csv_vs_database(csv_path: str):
    """Compare CSV data with database"""
    print("\n" + "=" * 80)
    print("COMPARISON: CSV vs DATABASE")
    print("=" * 80)
    
    db: Session = SessionLocal()
    
    try:
        # Get CSV society names
        csv_societies = set()
        with open(csv_path, 'r', encoding='utf-8') as file:
            next(file)  # Skip header
            reader = csv.reader(file)
            for row in reader:
                if len(row) > 4:
                    society_type = row[3].strip().strip('"').upper() if len(row) > 3 else ""
                    society_name = row[4].strip().strip('"') if len(row) > 4 else ""
                    if society_type == "SOCIETY" and society_name:
                        csv_societies.add(society_name.upper().strip())
        
        # Get database society names
        db_societies = {s.name.upper().strip() for s in db.query(Society).all()}
        
        # Find missing
        missing_in_db = csv_societies - db_societies
        extra_in_db = db_societies - csv_societies
        
        print(f"\n📊 Comparison Results:")
        print(f"   CSV Societies: {len(csv_societies)}")
        print(f"   DB Societies: {len(db_societies)}")
        print(f"   Missing in DB: {len(missing_in_db)}")
        print(f"   Extra in DB: {len(extra_in_db)}")
        print(f"   Match Rate: {(len(csv_societies & db_societies) / len(csv_societies) * 100):.1f}%")
        
        if missing_in_db:
            print(f"\n⚠️ Sample Missing in DB (first 10):")
            for name in list(missing_in_db)[:10]:
                print(f"   - {name}")
        
        if extra_in_db:
            print(f"\n➕ Extra in DB (first 10):")
            for name in list(extra_in_db)[:10]:
                print(f"   - {name}")
        
    finally:
        db.close()


if __name__ == "__main__":
    csv_file = "../../ Society.csv"
    
    print("🔍 Analyzing CSV and Database...")
    print(f"📁 CSV File: {csv_file}\n")
    
    csv_stats = analyze_csv(csv_file)
    analyze_database()
    compare_csv_vs_database(csv_file)
    
    print("\n" + "=" * 80)
    print("✅ Analysis Complete!")
    print("=" * 80)

