from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import FloatField, IntegerField, SelectField, SubmitField, HiddenField
from wtforms.validators import DataRequired, NumberRange, Optional

from app import db
from app.models.patient import Patient
from app.models.clinical_metrics import ClinicalMetrics
from app.models.risk_assessment import RiskAssessment
from app.models.audit_log import AuditLog, AuditAction
from app.ml.service import get_ml_service, ModelLoadError

risk_bp = Blueprint('risk', __name__, url_prefix='/risk')


class RiskPredictionForm(FlaskForm):
    """Form for GDM risk prediction with 10 core features."""
    
    # Hidden field for patient ID
    patient_id = HiddenField('Patient ID', validators=[DataRequired()])
    
    # Core clinical measurements
    age = IntegerField('Age (years)', validators=[
        DataRequired(message='Age is required'),
        NumberRange(min=12, max=60, message='Age must be between 12 and 60 years')
    ], render_kw={'class': 'form-control', 'placeholder': 'e.g., 28'})
    
    bmi = FloatField('BMI (kg/m²)', validators=[
        DataRequired(message='BMI is required'),
        NumberRange(min=10, max=60, message='BMI must be between 10 and 60')
    ], render_kw={'class': 'form-control', 'placeholder': 'e.g., 24.5', 'step': '0.1'})
    
    systolic_bp = IntegerField('Systolic Blood Pressure (mmHg)', validators=[
        DataRequired(message='Systolic BP is required'),
        NumberRange(min=70, max=250, message='Systolic BP must be between 70 and 250 mmHg')
    ], render_kw={'class': 'form-control', 'placeholder': 'e.g., 120'})
    
    diastolic_bp = IntegerField('Diastolic Blood Pressure (mmHg)', validators=[
        DataRequired(message='Diastolic BP is required'),
        NumberRange(min=40, max=150, message='Diastolic BP must be between 40 and 150 mmHg')
    ], render_kw={'class': 'form-control', 'placeholder': 'e.g., 80'})
    
    # Laboratory values (optional but recommended)
    hemoglobin = FloatField('Hemoglobin (g/dL)', validators=[
        Optional(),
        NumberRange(min=5, max=20, message='Hemoglobin must be between 5 and 20 g/dL')
    ], render_kw={'class': 'form-control', 'placeholder': 'e.g., 12.5', 'step': '0.1'})
    
    hdl_cholesterol = IntegerField('HDL Cholesterol (mg/dL)', validators=[
        Optional(),
        NumberRange(min=10, max=200, message='HDL cholesterol must be between 10 and 200 mg/dL')
    ], render_kw={'class': 'form-control', 'placeholder': 'e.g., 50'})
    
    # Pregnancy information
    pregnancies_count = IntegerField('Number of Pregnancies', validators=[
        DataRequired(message='Number of pregnancies is required'),
        NumberRange(min=1, max=20, message='Number of pregnancies must be between 1 and 20')
    ], render_kw={'class': 'form-control', 'placeholder': 'Including current pregnancy'})
    
    # Risk factors (boolean)
    family_history_diabetes = SelectField('Family History of Diabetes', choices=[
        (0, 'No'),
        (1, 'Yes')
    ], coerce=int, validators=[DataRequired()], render_kw={'class': 'form-select'})
    
    sedentary_lifestyle = SelectField('Sedentary Lifestyle', choices=[
        (0, 'No - Active lifestyle'),
        (1, 'Yes - Sedentary lifestyle')
    ], coerce=int, validators=[DataRequired()], render_kw={'class': 'form-select'})
    
    prediabetes_history = SelectField('History of Prediabetes', choices=[
        (0, 'No'),
        (1, 'Yes')
    ], coerce=int, validators=[DataRequired()], render_kw={'class': 'form-select'})
    
    submit = SubmitField('Predict GDM Risk', render_kw={'class': 'btn btn-primary btn-lg'})


@risk_bp.route('/predict/<int:patient_id>', methods=['GET', 'POST'])
@login_required
def predict_risk(patient_id):
    """Perform GDM risk prediction for a patient."""
    
    patient = Patient.query.get_or_404(patient_id)
    
    if not patient.is_active:
        flash('Cannot perform assessment on inactive patient record.', 'error')
        return redirect(url_for('patients.detail_patient', patient_id=patient_id))
    
    # Check if ML service is available
    ml_service = get_ml_service()
    ml_status = ml_service.get_status()
    
    form = RiskPredictionForm()
    form.patient_id.data = patient_id
    
    # Pre-fill form with patient data and latest clinical metrics if available
    if request.method == 'GET':
        # Always pre-fill patient demographic data
        form.age.data = patient.age
        
        # Use patient's parity for pregnancies count if available
        if patient.parity is not None:
            form.pregnancies_count.data = patient.parity + 1  # Add 1 for current pregnancy
        
        # Pre-fill from latest clinical metrics if available
        latest_metrics = patient.latest_clinical_metrics
        if latest_metrics:
            if latest_metrics.bmi:
                form.bmi.data = latest_metrics.bmi
            if latest_metrics.systolic_bp:
                form.systolic_bp.data = latest_metrics.systolic_bp
            if latest_metrics.diastolic_bp:
                form.diastolic_bp.data = latest_metrics.diastolic_bp
            if latest_metrics.hemoglobin:
                form.hemoglobin.data = latest_metrics.hemoglobin
            if latest_metrics.hdl_cholesterol:
                form.hdl_cholesterol.data = latest_metrics.hdl_cholesterol
            
            # Override pregnancies count if clinical metrics has more recent data
            if latest_metrics.pregnancies_count:
                form.pregnancies_count.data = latest_metrics.pregnancies_count
                
            # Pre-fill risk factors
            if latest_metrics.family_history_diabetes is not None:
                form.family_history_diabetes.data = 1 if latest_metrics.family_history_diabetes else 0
            if latest_metrics.sedentary_lifestyle is not None:
                form.sedentary_lifestyle.data = 1 if latest_metrics.sedentary_lifestyle else 0
            if latest_metrics.prediabetes_history is not None:
                form.prediabetes_history.data = 1 if latest_metrics.prediabetes_history else 0
    
    if form.validate_on_submit():
        if not ml_status['is_available']:
            flash(f'ML service is not available: {ml_status["load_error"]}', 'error')
            return redirect(url_for('risk.predict_risk', patient_id=patient_id))
        
        try:
            # Prepare input data for ML model
            input_data = {
                'age': form.age.data,
                'bmi': form.bmi.data,
                'systolic_bp': form.systolic_bp.data,
                'diastolic_bp': form.diastolic_bp.data,
                'hemoglobin': form.hemoglobin.data,
                'hdl_cholesterol': form.hdl_cholesterol.data,
                'pregnancies_count': form.pregnancies_count.data,
                'family_history_diabetes': form.family_history_diabetes.data,
                'sedentary_lifestyle': form.sedentary_lifestyle.data,
                'prediabetes_history': form.prediabetes_history.data
            }
            
            # Make prediction
            prediction_result = ml_service.predict_risk(input_data)
            
            # Create risk assessment record
            assessment = RiskAssessment(
                patient_id=patient.id,
                assessed_by=current_user.id,
                input_vector=input_data,
                risk_score=prediction_result['risk_score'],
                model_version=prediction_result['model_version']
            )
            
            # Save to database
            db.session.add(assessment)
            db.session.commit()
            
            # Log the assessment
            AuditLog.log_assessment_action(
                action=AuditAction.PERFORM_ASSESSMENT,
                assessment_id=assessment.id,
                user_id=current_user.id,
                details=f"Risk assessment for {patient.full_name}: {assessment.risk_label} ({assessment.risk_percentage}%)"
            )
            
            flash(f'Risk assessment completed for {patient.full_name}!', 'success')
            return redirect(url_for('risk.view_assessment', assessment_id=assessment.id))
            
        except (ModelLoadError, ValueError, RuntimeError) as e:
            flash(f'Prediction failed: {str(e)}', 'error')
        except Exception as e:
            db.session.rollback()
            flash('An error occurred during risk assessment. Please try again.', 'error')
    
    return render_template(
        'risk/predict.html',
        form=form,
        patient=patient,
        latest_metrics=patient.latest_clinical_metrics,
        ml_status=ml_status,
        reference_ranges=ml_service.get_reference_ranges(),
        breadcrumbs=[
            {'name': 'Dashboard', 'url': url_for('core.dashboard')},
            {'name': 'Patients', 'url': url_for('patients.list_patients')},
            {'name': patient.full_name, 'url': url_for('patients.detail_patient', patient_id=patient.id)},
            {'name': 'Risk Assessment', 'url': url_for('risk.predict_risk', patient_id=patient.id)}
        ]
    )


@risk_bp.route('/assessments/<int:assessment_id>')
@login_required
def view_assessment(assessment_id):
    """View detailed risk assessment results."""
    
    assessment = RiskAssessment.query.get_or_404(assessment_id)
    patient = assessment.patient
    
    # Get ML service for additional info
    ml_service = get_ml_service()
    feature_importance = ml_service.get_feature_importance()
    reference_ranges = ml_service.get_reference_ranges()
    
    # Log the view
    AuditLog.log_assessment_action(
        action=AuditAction.VIEW_ASSESSMENT,
        assessment_id=assessment.id,
        user_id=current_user.id
    )
    
    return render_template(
        'risk/results.html',
        assessment=assessment,
        patient=patient,
        feature_importance=feature_importance,
        reference_ranges=reference_ranges,
        breadcrumbs=[
            {'name': 'Dashboard', 'url': url_for('core.dashboard')},
            {'name': 'Patients', 'url': url_for('patients.list_patients')},
            {'name': patient.full_name, 'url': url_for('patients.detail_patient', patient_id=patient.id)},
            {'name': f'Assessment Results', 'url': url_for('risk.view_assessment', assessment_id=assessment.id)}
        ]
    )


@risk_bp.route('/api/model-status')
@login_required
def api_model_status():
    """API endpoint to check ML model status."""
    
    ml_service = get_ml_service()
    status = ml_service.get_status()
    
    return jsonify(status)


@risk_bp.route('/api/reference-ranges')
@login_required  
def api_reference_ranges():
    """API endpoint to get clinical reference ranges."""
    
    ml_service = get_ml_service()
    ranges = ml_service.get_reference_ranges()
    
    return jsonify(ranges)


@risk_bp.route('/assessments')
@login_required
def list_assessments():
    """List recent risk assessments."""
    
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Get recent assessments with pagination
    assessments = RiskAssessment.query.order_by(
        RiskAssessment.created_at.desc()
    ).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    # Get summary statistics
    stats = RiskAssessment.get_statistics()
    
    return render_template(
        'risk/assessments_list.html',
        assessments=assessments,
        stats=stats,
        breadcrumbs=[
            {'name': 'Dashboard', 'url': url_for('core.dashboard')},
            {'name': 'Risk Assessments', 'url': url_for('risk.list_assessments')}
        ]
    )


@risk_bp.route('/api/predict', methods=['POST'])
@login_required
def api_predict():
    """API endpoint for risk prediction (for AJAX calls)."""
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Get ML service
        ml_service = get_ml_service()
        
        if not ml_service.is_available():
            return jsonify({'error': 'ML service not available'}), 503
        
        # Make prediction
        result = ml_service.predict_risk(data)
        
        return jsonify(result)
        
    except (ValueError, ModelLoadError) as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'Prediction failed'}), 500