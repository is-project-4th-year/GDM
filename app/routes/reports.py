"""
Reports Routes for GDM Risk Assessment System
"""
import os
from flask import Blueprint, render_template, request, flash, redirect, url_for, send_file, jsonify, abort, current_app
from flask_login import login_required, current_user
from werkzeug.exceptions import NotFound

# Import db from flask current_app context to avoid circular import
from flask_sqlalchemy import SQLAlchemy

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')


def get_db():
    """Get database instance from current app context."""
    return current_app.extensions['sqlalchemy'].db


@reports_bp.route('/')
@login_required
def list_reports():
    """List all reports with filtering and pagination."""
    
    # Import models locally to avoid circular imports
    from app.models.report import Report
    from app.models.patient import Patient
    from app.models.audit_log import AuditLog, AuditAction
    
    page = request.args.get('page', 1, type=int)
    per_page = 10
    patient_filter = request.args.get('patient_id', type=int)
    
    # Build query
    query = Report.query.filter_by(is_active=True)
    
    if patient_filter:
        query = query.filter_by(patient_id=patient_filter)
    
    # Order by creation date (newest first)
    query = query.order_by(Report.generated_at.desc())
    
    # Paginate results
    reports = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    # Get patients for filter dropdown
    patients = Patient.query.filter_by(is_active=True).order_by(Patient.first_name, Patient.last_name).all()
    
    # Log the access
    AuditLog.log_action(
        action=AuditAction.VIEW_PATIENT,
        user_id=current_user.id,
        details=f"Viewed reports list, page {page}"
    )
    
    return render_template(
        'reports/list.html',
        reports=reports,
        patients=patients,
        selected_patient=patient_filter,
        breadcrumbs=[
            {'name': 'Dashboard', 'url': url_for('core.dashboard')},
            {'name': 'Reports', 'url': url_for('reports.list_reports')}
        ]
    )


@reports_bp.route('/generate/<int:assessment_id>', methods=['POST'])
@login_required
def generate_report(assessment_id):
    """Generate a new PDF report for a risk assessment."""
    
    from app.models.risk_assessment import RiskAssessment
    from app.services.pdf_service import PDFReportService
    
    assessment = RiskAssessment.query.get_or_404(assessment_id)
    
    # Check if assessment belongs to active patient
    if not assessment.patient.is_active:
        flash('Cannot generate report for inactive patient.', 'error')
        return redirect(url_for('patients.detail_patient', patient_id=assessment.patient.id))
    
    try:
        # Initialize PDF service
        pdf_service = PDFReportService()
        
        # Generate the report
        include_recommendations = request.form.get('include_recommendations', 'on') == 'on'
        report = pdf_service.generate_risk_assessment_report(
            risk_assessment=assessment,
            user_id=current_user.id,
            include_recommendations=include_recommendations
        )
        
        flash(f'Report generated successfully for {assessment.patient.full_name}!', 'success')
        return redirect(url_for('reports.view_report', report_id=report.id))
        
    except Exception as e:
        flash(f'Error generating report: {str(e)}', 'error')
        return redirect(url_for('risk.view_assessment', assessment_id=assessment_id))


@reports_bp.route('/preview/<int:assessment_id>')
@login_required
def preview_report(assessment_id):
    """Preview report before generating PDF."""
    
    from app.models.risk_assessment import RiskAssessment
    from app.models.audit_log import AuditLog, AuditAction
    from app.services.pdf_service import PDFReportService
    
    assessment = RiskAssessment.query.get_or_404(assessment_id)
    
    if not assessment.patient.is_active:
        flash('Cannot preview report for inactive patient.', 'warning')
        return redirect(url_for('patients.detail_patient', patient_id=assessment.patient.id))
    
    # Prepare data for preview (same as PDF service would use)
    pdf_service = PDFReportService()
    report_data = pdf_service._prepare_report_data(assessment, include_recommendations=True)
    
    # Log the preview action
    AuditLog.log_action(
        action=AuditAction.VIEW_PATIENT,
        user_id=current_user.id,
        details=f"Previewed report for assessment {assessment_id}"
    )
    
    return render_template(
        'reports/preview.html',
        assessment=assessment,
        **report_data,
        breadcrumbs=[
            {'name': 'Dashboard', 'url': url_for('core.dashboard')},
            {'name': 'Patients', 'url': url_for('patients.list_patients')},
            {'name': assessment.patient.full_name, 'url': url_for('patients.detail_patient', patient_id=assessment.patient.id)},
            {'name': 'Report Preview', 'url': url_for('reports.preview_report', assessment_id=assessment_id)}
        ]
    )

@reports_bp.route('/view/<int:report_id>')
@login_required
def view_report(report_id):
    """View report details and download options (reuses preview layout)."""
    
    from app.models.report import Report
    from app.models.audit_log import AuditLog, AuditAction
    from app.services.pdf_service import PDFReportService

    report = Report.query.get_or_404(report_id)

    if not report.is_active:
        flash('This report is no longer available.', 'warning')
        return redirect(url_for('reports.list_reports'))

    # Get the linked assessment
    assessment = report.risk_assessment
    if assessment is None:
        flash('This report is not linked to a risk assessment.', 'error')
        return redirect(url_for('reports.list_reports'))

    # Use the same data-prep helper as the preview route
    pdf_service = PDFReportService()
    report_data = pdf_service._prepare_report_data(
        assessment,
        include_recommendations=True
    )

    # Log the view action
    AuditLog.log_action(
        action=AuditAction.VIEW_PATIENT,  # or a VIEW_REPORT action if you have one
        user_id=current_user.id,
        details=f"Viewed report {report.uuid}"
    )

    return render_template(
        'reports/preview.html',
        report=report,
        assessment=assessment,
        **report_data,  # provides patient, risk_assessment, input_data, etc.
        breadcrumbs=[
            {'name': 'Dashboard', 'url': url_for('core.dashboard')},
            {'name': 'Reports', 'url': url_for('reports.list_reports')},
            {'name': report.title, 'url': url_for('reports.view_report', report_id=report.id)}
        ]
    )

# @reports_bp.route('/view/<int:report_id>')
# @login_required
# def view_report(report_id):
#     """View report details and download options."""
    
#     from app.models.report import Report
#     from app.models.audit_log import AuditLog, AuditAction
    
#     report = Report.query.get_or_404(report_id)
    
#     if not report.is_active:
#         flash('This report is no longer available.', 'warning')
#         return redirect(url_for('reports.list_reports'))
    
#     # Log the view action
#     AuditLog.log_action(
#         action=AuditAction.VIEW_PATIENT,
#         user_id=current_user.id,
#         details=f"Viewed report {report.uuid}"
#     )
    
#     return render_template(
#         'reports/preview.html',
#         report=report,
#         breadcrumbs=[
#             {'name': 'Dashboard', 'url': url_for('core.dashboard')},
#             {'name': 'Reports', 'url': url_for('reports.list_reports')},
#             {'name': report.title, 'url': url_for('reports.view_report', report_id=report.id)}
#         ]
#     )


@reports_bp.route('/download/<int:report_id>')
@login_required
def download_report(report_id):
    """Download PDF report file."""
    
    from app.models.report import Report
    from app.models.audit_log import AuditLog, AuditAction
    
    report = Report.query.get_or_404(report_id)
    
    if not report.is_active:
        abort(404)
    
    if not report.pdf_path or not os.path.exists(report.pdf_path):
        flash('Report file not found. Please regenerate the report.', 'error')
        return redirect(url_for('reports.view_report', report_id=report_id))
    
    try:
        # Log the download
        AuditLog.log_action(
            action=AuditAction.DOWNLOAD_REPORT,
            user_id=current_user.id,
            entity="report",
            entity_id=report.id,
            details=f"Downloaded report: {report.title}"
        )
        
        return send_file(
            report.pdf_path,
            as_attachment=True,
            download_name=report.download_filename,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        flash(f'Error downloading report: {str(e)}', 'error')
        return redirect(url_for('reports.view_report', report_id=report_id))


@reports_bp.route('/delete/<int:report_id>', methods=['POST'])
@login_required
def delete_report(report_id):
    """Soft delete a report."""
    
    from app.models.report import Report
    from app.models.audit_log import AuditLog, AuditAction
    from app.services.pdf_service import PDFReportService
    
    report = Report.query.get_or_404(report_id)
    
    # Only allow admin or the generator to delete
    if current_user.role != 'admin' and report.generated_by != current_user.id:
        flash('You do not have permission to delete this report.', 'error')
        return redirect(url_for('reports.view_report', report_id=report_id))
    
    try:
        # Soft delete the report
        report.soft_delete()
        
        # Optionally delete the physical file
        if request.form.get('delete_file') == 'on':
            pdf_service = PDFReportService()
            pdf_service.delete_report_file(report)
        
        # Log the deletion
        AuditLog.log_action(
            action=AuditAction.DELETE_REPORT,
            user_id=current_user.id,
            entity="report", 
            entity_id=report.id,
            details=f"Deleted report: {report.title}"
        )
        
        flash('Report deleted successfully.', 'success')
        return redirect(url_for('reports.list_reports'))
        
    except Exception as e:
        flash(f'Error deleting report: {str(e)}', 'error')
        return redirect(url_for('reports.view_report', report_id=report_id))


@reports_bp.route('/api/stats')
@login_required
def api_report_stats():
    """Get report statistics for dashboard."""
    
    from app.models.report import Report
    from datetime import datetime, timedelta
    
    total_reports = Report.query.filter_by(is_active=True).count()
    
    # Reports generated this month
    month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    reports_this_month = Report.query.filter(
        Report.is_active == True,
        Report.generated_at >= month_start
    ).count()
    
    # Reports by current user
    user_reports = Report.query.filter_by(
        generated_by=current_user.id,
        is_active=True
    ).count()
    
    # Recent reports
    recent_reports = Report.get_recent_reports(limit=5)
    recent_reports_data = [report.to_dict() for report in recent_reports]
    
    return jsonify({
        'total_reports': total_reports,
        'reports_this_month': reports_this_month,
        'user_reports': user_reports,
        'recent_reports': recent_reports_data
    })