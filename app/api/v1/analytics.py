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
from app.models.organization import Branch
from app.dependencies.auth import get_current_user
from fastapi import status

router = APIRouter()


def get_admin_or_branch_manager(
    current_user: User = Depends(get_current_user)
) -> User:
    """Dependency that allows admin or branch manager"""
    admin_roles = ["super_admin", "mahasewa_admin", "mahasewa_staff", "branch_manager"]
    if current_user.role not in admin_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or branch manager access required"
        )
    return current_user


@router.get("/admin/branch-analytics")
async def get_branch_analytics(
    branch_id: Optional[int] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_or_branch_manager)
):
    """
    Get branch analytics data
    
    Access:
    - Admins: Can see all branches or filter by branch_id
    - Branch Managers: Can only see their own branch data
    """
    # Branch managers can only see their own branch
    if current_user.role == "branch_manager":
        manager_branch = db.query(Branch).filter(Branch.manager_id == current_user.id).first()
        if manager_branch:
            branch_id = manager_branch.id
        else:
            # Manager has no branch assigned, return empty data
            return {
                "branches": [],
                "summary": {
                    "total_members": 0,
                    "total_bookings": 0,
                    "total_consultations": 0,
                    "total_cases": 0,
                    "total_revenue": 0.0
                },
                "date_range": {
                    "start_date": start_date or "all",
                    "end_date": end_date or "all"
                }
            }
    
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
    current_user: User = Depends(get_admin_or_branch_manager)
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
    
    # Generate PDF file
    if format == "pdf":
        try:
            from weasyprint import HTML
            import io
            
            # Create HTML content for PDF
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        @page {{
            size: A4 landscape;
            margin: 2cm;
        }}
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 3px solid #f97316;
        }}
        .header h1 {{
            color: #f97316;
            margin: 0;
        }}
        .summary {{
            background-color: #f9f9f9;
            padding: 20px;
            margin-bottom: 30px;
            border-radius: 5px;
        }}
        .summary h2 {{
            margin-top: 0;
            color: #333;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        th {{
            background-color: #f97316;
            color: white;
            font-weight: bold;
        }}
        tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        .total-row {{
            background-color: #fff3cd;
            font-weight: bold;
        }}
        .footer {{
            margin-top: 30px;
            text-align: center;
            color: #666;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Branch Analytics Report</h1>
        <p>MahaSeWA - Maharashtra Societies Welfare Association</p>
        <p>Period: {analytics_data['date_range']['start_date']} to {analytics_data['date_range']['end_date']}</p>
    </div>
    
    <div class="summary">
        <h2>Summary</h2>
        <p><strong>Total Members:</strong> {analytics_data['summary']['total_members']}</p>
        <p><strong>Total Bookings:</strong> {analytics_data['summary']['total_bookings']}</p>
        <p><strong>Total Consultations:</strong> {analytics_data['summary']['total_consultations']}</p>
        <p><strong>Total Cases:</strong> {analytics_data['summary']['total_cases']}</p>
        <p><strong>Total Revenue:</strong> ₹{analytics_data['summary']['total_revenue']:,.2f}</p>
    </div>
    
    <table>
        <thead>
            <tr>
                <th>Branch</th>
                <th>Branch Code</th>
                <th>City</th>
                <th>Members</th>
                <th>Bookings</th>
                <th>Revenue (₹)</th>
                <th>Cases</th>
            </tr>
        </thead>
        <tbody>
            {''.join([
                f"<tr><td>{branch['branch_name']}</td><td>{branch.get('branch_code', 'N/A')}</td><td>{branch.get('city', 'N/A')}</td><td>{branch['members']}</td><td>{branch['bookings']}</td><td>{branch['revenue']:,.2f}</td><td>{branch['cases']}</td></tr>"
                for branch in analytics_data['branches']
            ])}
            <tr class="total-row">
                <td colspan="3"><strong>TOTAL</strong></td>
                <td><strong>{analytics_data['summary']['total_members']}</strong></td>
                <td><strong>{analytics_data['summary']['total_bookings']}</strong></td>
                <td><strong>₹{analytics_data['summary']['total_revenue']:,.2f}</strong></td>
                <td><strong>{analytics_data['summary']['total_cases']}</strong></td>
            </tr>
        </tbody>
    </table>
    
    <div class="footer">
        <p>Generated on {datetime.now().strftime('%d-%b-%Y %H:%M:%S')}</p>
        <p>MahaSeWA - Maharashtra Societies Welfare Association</p>
    </div>
</body>
</html>
            """
            
            # Generate PDF
            pdf_bytes = HTML(string=html_content).write_pdf()
            
            from fastapi.responses import StreamingResponse
            return StreamingResponse(
                io.BytesIO(pdf_bytes),
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename=branch-report-{datetime.now().strftime('%Y%m%d')}.pdf"}
            )
        except ImportError:
            raise HTTPException(
                status_code=503,
                detail="PDF generation requires WeasyPrint. Please install: pip install weasyprint"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error generating PDF: {str(e)}"
            )
    
    raise HTTPException(status_code=400, detail="Unsupported format. Use 'excel' or 'pdf'")
