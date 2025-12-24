"""
Branch Analytics Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import Optional
from datetime import datetime, date

from app.db.session import get_db
from app.models.member import Member
from app.models.booking import ServiceBooking
from app.models.consultation import Consultation
from app.models.case import Case
from app.models.organization import Branch
from app.models.user import User
from app.api.v1.admin import get_current_admin_user

router = APIRouter()


@router.get("/admin/branch-analytics")
async def get_branch_analytics(
    branch_id: Optional[int] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get branch analytics data"""
    try:
        # Parse dates
        start = datetime.fromisoformat(start_date) if start_date else date.today().replace(month=1, day=1)
        end = datetime.fromisoformat(end_date) if end_date else datetime.now()
        
        if isinstance(start, date):
            start = datetime.combine(start, datetime.min.time())
        if isinstance(end, date):
            end = datetime.combine(end, datetime.max.time())
        
        # Base query filters
        date_filter = and_(
            func.date(Member.created_at) >= start.date(),
            func.date(Member.created_at) <= end.date()
        )
        
        # Get summary stats
        members_query = db.query(Member).filter(date_filter)
        bookings_query = db.query(ServiceBooking).filter(
            ServiceBooking.created_at >= start,
            ServiceBooking.created_at <= end
        )
        consultations_query = db.query(Consultation).filter(
            Consultation.created_at >= start,
            Consultation.created_at <= end
        )
        cases_query = db.query(Case).filter(
            Case.start_date >= start.date(),
            Case.start_date <= end.date()
        )
        
        # Filter by branch if specified
        if branch_id:
            members_query = members_query.filter(Member.branch_id == branch_id)
            bookings_query = bookings_query.filter(ServiceBooking.branch_id == branch_id)
            consultations_query = consultations_query.filter(Consultation.branch_id == branch_id)
            cases_query = cases_query.filter(Case.branch_id == branch_id)
        
        # Calculate totals
        total_members = members_query.count()
        total_bookings = bookings_query.count()
        total_consultations = consultations_query.count()
        total_cases = cases_query.count()
        
        # Calculate revenue (from invoices if available)
        # Note: Invoice model may not exist yet - handle gracefully
        total_revenue = 0.0
        try:
            from app.models.invoice import Invoice
            revenue_query = db.query(func.sum(Invoice.total_amount)).filter(
                Invoice.created_at >= start,
                Invoice.created_at <= end
            )
            if branch_id:
                revenue_query = revenue_query.filter(Invoice.branch_id == branch_id)
            total_revenue = float(revenue_query.scalar() or 0)
        except ImportError:
            # Invoice model doesn't exist yet
            pass
        
        # Branch-wise breakdown (if all branches)
        branches_data = []
        if not branch_id:
            branches = db.query(Branch).filter(Branch.is_active == True).all()
            for branch in branches:
                branch_members = members_query.filter(Member.branch_id == branch.id).count()
                branch_bookings = bookings_query.filter(ServiceBooking.branch_id == branch.id).count()
                branch_revenue = 0.0
                try:
                    from app.models.invoice import Invoice
                    branch_revenue = float(db.query(func.sum(Invoice.total_amount)).filter(
                        Invoice.branch_id == branch.id,
                        Invoice.created_at >= start,
                        Invoice.created_at <= end
                    ).scalar() or 0)
                except ImportError:
                    pass
                branch_cases = cases_query.filter(Case.branch_id == branch.id).count()
                
                branches_data.append({
                    'branch_id': branch.id,
                    'branch_name': branch.name,
                    'branch_code': branch.code,
                    'city': branch.city,
                    'members': branch_members,
                    'bookings': branch_bookings,
                    'revenue': branch_revenue,
                    'cases': branch_cases,
                })
        
        return {
            'summary': {
                'total_members': total_members,
                'total_bookings': total_bookings,
                'total_consultations': total_consultations,
                'total_cases': total_cases,
                'total_revenue': total_revenue,
            },
            'branches': branches_data,
            'date_range': {
                'start_date': start.isoformat(),
                'end_date': end.isoformat(),
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating analytics: {str(e)}")


@router.get("/admin/branch-reports/generate")
async def generate_branch_report(
    branch_id: Optional[int] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    format: str = Query("excel"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Generate branch report in Excel or PDF format"""
    # Get analytics data
    analytics_data = await get_branch_analytics(
        branch_id=branch_id,
        start_date=start_date,
        end_date=end_date,
        db=db,
        current_user=current_user
    )
    
    # Generate Excel file
    if format == "excel":
        try:
            import io
            from openpyxl import Workbook
            
            wb = Workbook()
            ws = wb.active
            ws.title = "Branch Analytics"
            
            # Headers
            ws.append(['Branch', 'Members', 'Bookings', 'Revenue', 'Cases'])
            
            # Data
            for branch in analytics_data['branches']:
                ws.append([
                    branch['branch_name'],
                    branch['members'],
                    branch['bookings'],
                    branch['revenue'],
                    branch['cases'],
                ])
            
            # Summary row
            ws.append(['TOTAL', 
                      analytics_data['summary']['total_members'],
                      analytics_data['summary']['total_bookings'],
                      analytics_data['summary']['total_revenue'],
                      analytics_data['summary']['total_cases']])
            
            # Save to bytes
            output = io.BytesIO()
            wb.save(output)
            output.seek(0)
            
            from fastapi.responses import StreamingResponse
            return StreamingResponse(
                output,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f"attachment; filename=branch-report.xlsx"}
            )
        except ImportError:
            # Fallback to CSV if openpyxl not available
            import csv
            import io
            from fastapi.responses import Response
            
            csv_data = []
            csv_data.append(['Branch', 'Members', 'Bookings', 'Revenue', 'Cases'])
            for branch in analytics_data['branches']:
                csv_data.append([
                    branch['branch_name'],
                    branch['members'],
                    branch['bookings'],
                    branch['revenue'],
                    branch['cases'],
                ])
            csv_data.append(['TOTAL',
                            analytics_data['summary']['total_members'],
                            analytics_data['summary']['total_bookings'],
                            analytics_data['summary']['total_revenue'],
                            analytics_data['summary']['total_cases']])
            
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerows(csv_data)
            
            return Response(
                content=output.getvalue(),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=branch-report.csv"}
            )
    
    raise HTTPException(status_code=400, detail="Unsupported format. Use 'excel'")
