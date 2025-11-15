from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from sqlalchemy import or_, and_
from datetime import date

from app import db
from app.models.patient import Patient
from app.models.clinical_metrics import ClinicalMetrics
from app.models.audit_log import AuditLog, AuditAction
from app.forms.patient_forms import PatientForm, PatientSearchForm, ClinicalMetricsForm

patients_bp = Blueprint('patients', __name__, url_prefix='/patients')


@patients_bp.route('/')
@login_required
def list_patients():
    """List all patients with search and pagination."""
    
    search_form = PatientSearchForm()
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Number of patients per page
    
    # Get search query from form or URL parameter
    search_query = request.args.get('search', '').strip()
    if search_form.validate_on_submit():
        search_query = search_form.search_query.data.strip()
    
    # Build query
    query = Patient.query.filter_by(is_active=True)
    
    if search_query:
        # Search in multiple fields
        search_pattern = f"%{search_query}%"
        query = query.filter(
            or_(
                Patient.first_name.ilike(search_pattern),
                Patient.last_name.ilike(search_pattern),
                Patient.phone.ilike(search_pattern),
                Patient.national_id.ilike(search_pattern) if search_query else False
            )
        )
    
    # Order by creation date (newest first)
    query = query.order_by(Patient.created_at.desc())
    
    # Paginate results
    patients = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    # Log the patient list access
    AuditLog.log_action(
        action=AuditAction.VIEW_PATIENT,
        user_id=current_user.id,
        details=f"Viewed patient list, page {page}" + (f", search: {search_query}" if search_query else "")
    )
    
    return render_template(
        'patients/list.html',
        patients=patients,
        search_form=search_form,
        search_query=search_query,
        breadcrumbs=[
            {'name': 'Dashboard', 'url': url_for('core.dashboard')},
            {'name': 'Patients', 'url': url_for('patients.list_patients')}
        ]
    )


@patients_bp.route('/new', methods=['GET', 'POST'])
@login_required
def create_patient():
    """Create a new patient."""
    
    form = PatientForm()
    
    if form.validate_on_submit():
        try:
            # Create new patient
            patient = Patient(
                first_name=form.first_name.data.strip(),
                last_name=form.last_name.data.strip(),
                date_of_birth=form.date_of_birth.data,
                created_by=current_user.id,
                national_id=form.national_id.data.strip() if form.national_id.data else None,
                phone=form.phone.data.strip() if form.phone.data else None,
                parity=form.parity.data,
                gestational_age_weeks=form.gestational_age_weeks.data
            )
            
            # Save to database
            db.session.add(patient)
            db.session.commit()
            
            # Log the action
            AuditLog.log_patient_action(
                action=AuditAction.CREATE_PATIENT,
                patient_id=patient.id,
                user_id=current_user.id,
                details=f"Created patient: {patient.full_name}"
            )
            
            flash(f'Patient {patient.full_name} created successfully!', 'success')
            return redirect(url_for('patients.detail_patient', patient_id=patient.id))
            
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while creating the patient. Please try again.', 'error')
    
    return render_template(
        'patients/create.html',
        form=form,
        breadcrumbs=[
            {'name': 'Dashboard', 'url': url_for('core.dashboard')},
            {'name': 'Patients', 'url': url_for('patients.list_patients')},
            {'name': 'New Patient', 'url': url_for('patients.create_patient')}
        ]
    )


@patients_bp.route('/<int:patient_id>')
@login_required
def detail_patient(patient_id):
    """View patient details with latest clinical metrics and assessments."""
    
    patient = Patient.query.get_or_404(patient_id)
    
    if not patient.is_active:
        flash('This patient record is not active.', 'warning')
        return redirect(url_for('patients.list_patients'))
    
    # Get latest clinical metrics
    latest_metrics = patient.latest_clinical_metrics
    
    # Get latest risk assessment
    latest_assessment = patient.latest_risk_assessment
    
    # Get recent clinical metrics (last 5)
    recent_metrics = patient.get_clinical_metrics_history(limit=5)
    
    # Get recent assessments (last 3)
    recent_assessments = patient.get_risk_assessment_history(limit=3)
    
    # Log the patient view
    AuditLog.log_patient_action(
        action=AuditAction.VIEW_PATIENT,
        patient_id=patient.id,
        user_id=current_user.id
    )
    
    return render_template(
        'patients/detail.html',
        patient=patient,
        latest_metrics=latest_metrics,
        latest_assessment=latest_assessment,
        recent_metrics=recent_metrics,
        recent_assessments=recent_assessments,
        breadcrumbs=[
            {'name': 'Dashboard', 'url': url_for('core.dashboard')},
            {'name': 'Patients', 'url': url_for('patients.list_patients')},
            {'name': patient.full_name, 'url': url_for('patients.detail_patient', patient_id=patient.id)}
        ]
    )

@patients_bp.route('/<int:patient_id>/metrics/new', methods=['GET', 'POST'])
@login_required
def add_clinical_metrics(patient_id):
    """Add clinical metrics for a patient - Redirect to risk assessment."""
    
    patient = Patient.query.get_or_404(patient_id)
    
    if not patient.is_active:
        flash('Cannot add metrics to an inactive patient record.', 'error')
        return redirect(url_for('patients.detail_patient', patient_id=patient_id))
    
    # Since clinical metrics are entered during risk assessment, 
    # redirect to the risk assessment page
    flash(f'Add clinical metrics for {patient.full_name} during the risk assessment.', 'info')
    return redirect(url_for('risk.predict_risk', patient_id=patient_id))


@patients_bp.route('/<int:patient_id>/history')
@login_required
def patient_history(patient_id):
    """View complete patient history including all metrics and assessments."""
    
    patient = Patient.query.get_or_404(patient_id)
    
    if not patient.is_active:
        flash('This patient record is not active.', 'warning')
        return redirect(url_for('patients.list_patients'))
    
    # Get all clinical metrics ordered by date
    all_metrics = patient.get_clinical_metrics_history()
    
    # Get all risk assessments ordered by date
    all_assessments = patient.get_risk_assessment_history()
    
    # Get all reports for this patient
    from app.models.report import Report
    all_reports = Report.get_reports_for_patient(patient_id)
    
    # Log the history view
    AuditLog.log_patient_action(
        action=AuditAction.VIEW_PATIENT,
        patient_id=patient.id,
        user_id=current_user.id,
        details="Viewed patient history"
    )
    
    return render_template(
        'patients/history.html',
        patient=patient,
        all_metrics=all_metrics,
        all_assessments=all_assessments,
        all_reports=all_reports,
        breadcrumbs=[
            {'name': 'Dashboard', 'url': url_for('core.dashboard')},
            {'name': 'Patients', 'url': url_for('patients.list_patients')},
            {'name': patient.full_name, 'url': url_for('patients.detail_patient', patient_id=patient.id)},
            {'name': 'History', 'url': url_for('patients.patient_history', patient_id=patient.id)}
        ]
    )


@patients_bp.route('/<int:patient_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_patient(patient_id):
    """Edit patient information."""
    
    patient = Patient.query.get_or_404(patient_id)
    
    if not patient.is_active:
        flash('Cannot edit an inactive patient record.', 'error')
        return redirect(url_for('patients.detail_patient', patient_id=patient_id))
    
    form = PatientForm(obj=patient)
    form.patient_id = patient.id  # For validation
    
    if form.validate_on_submit():
        try:
            # Update patient fields
            patient.first_name = form.first_name.data.strip()
            patient.last_name = form.last_name.data.strip()
            patient.date_of_birth = form.date_of_birth.data
            patient.national_id = form.national_id.data.strip() if form.national_id.data else None
            patient.phone = form.phone.data.strip() if form.phone.data else None
            patient.parity = form.parity.data
            patient.gestational_age_weeks = form.gestational_age_weeks.data
            
            # Save to database
            db.session.commit()
            
            # Log the action
            AuditLog.log_patient_action(
                action=AuditAction.UPDATE_PATIENT,
                patient_id=patient.id,
                user_id=current_user.id,
                details=f"Updated patient: {patient.full_name}"
            )
            
            flash(f'Patient {patient.full_name} updated successfully!', 'success')
            return redirect(url_for('patients.detail_patient', patient_id=patient.id))
            
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while updating the patient. Please try again.', 'error')
    
    return render_template(
        'patients/edit.html',
        form=form,
        patient=patient,
        breadcrumbs=[
            {'name': 'Dashboard', 'url': url_for('core.dashboard')},
            {'name': 'Patients', 'url': url_for('patients.list_patients')},
            {'name': patient.full_name, 'url': url_for('patients.detail_patient', patient_id=patient.id)},
            {'name': 'Edit', 'url': url_for('patients.edit_patient', patient_id=patient.id)}
        ]
    )


@patients_bp.route('/api/search')
@login_required
def api_search_patients():
    """API endpoint for patient search (for autocomplete)."""
    
    query = request.args.get('q', '').strip()
    limit = min(int(request.args.get('limit', 10)), 50)  # Max 50 results
    
    if len(query) < 2:
        return jsonify([])
    
    patients = Patient.search(query, limit=limit)
    
    results = []
    for patient in patients:
        results.append({
            'id': patient.id,
            'uuid': patient.uuid,
            'full_name': patient.full_name,
            'age': patient.age,
            'phone': patient.phone,
            'assessment_count': patient.assessment_count
        })
    
    return jsonify(results)


@patients_bp.route('/stats')
@login_required
def patient_statistics():
    """Get patient statistics for dashboard."""
    
    total_patients = Patient.query.filter_by(is_active=True).count()
    
    # Patients created this month
    from datetime import datetime, timedelta
    month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    patients_this_month = Patient.query.filter(
        Patient.is_active == True,
        Patient.created_at >= month_start
    ).count()
    
    # Patients with recent assessments (last 30 days)
    recent_cutoff = datetime.now() - timedelta(days=30)
    from app.models.risk_assessment import RiskAssessment
    patients_with_recent_assessments = db.session.query(Patient).join(RiskAssessment).filter(
        Patient.is_active == True,
        RiskAssessment.created_at >= recent_cutoff
    ).distinct().count()
    
    stats = {
        'total_patients': total_patients,
        'patients_this_month': patients_this_month,
        'patients_with_recent_assessments': patients_with_recent_assessments,
        'completion_rate': round((patients_with_recent_assessments / total_patients * 100), 1) if total_patients > 0 else 0
    }
    
    return jsonify(stats)