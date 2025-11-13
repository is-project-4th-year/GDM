from flask_wtf import FlaskForm
from wtforms import StringField, DateField, IntegerField, SubmitField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Length, Optional, NumberRange, ValidationError
from datetime import date, timedelta
from app.models.patient import Patient


class PatientForm(FlaskForm):
    """Form for creating and editing patients."""
    
    first_name = StringField('First Name', validators=[
        DataRequired(message='First name is required'),
        Length(min=2, max=50, message='First name must be between 2 and 50 characters')
    ], render_kw={'placeholder': 'Enter first name', 'class': 'form-control'})
    
    last_name = StringField('Last Name', validators=[
        DataRequired(message='Last name is required'),
        Length(min=2, max=50, message='Last name must be between 2 and 50 characters')
    ], render_kw={'placeholder': 'Enter last name', 'class': 'form-control'})
    
    date_of_birth = DateField('Date of Birth', validators=[
        DataRequired(message='Date of birth is required')
    ], render_kw={'class': 'form-control'})
    
    national_id = StringField('National ID / SSN', validators=[
        Optional(),
        Length(max=50, message='National ID must be less than 50 characters')
    ], render_kw={'placeholder': 'Optional - National ID, SSN, etc.', 'class': 'form-control'})
    
    phone = StringField('Phone Number', validators=[
        Optional(),
        Length(max=20, message='Phone number must be less than 20 characters')
    ], render_kw={'placeholder': 'Optional - +1 234 567 8900', 'class': 'form-control'})
    
    parity = IntegerField('Parity (Previous Pregnancies)', validators=[
        Optional(),
        NumberRange(min=0, max=20, message='Parity must be between 0 and 20')
    ], render_kw={'placeholder': 'Number of previous pregnancies', 'class': 'form-control', 'min': '0', 'max': '20'})
    
    gestational_age_weeks = IntegerField('Current Gestational Age (Weeks)', validators=[
        Optional(),
        NumberRange(min=1, max=42, message='Gestational age must be between 1 and 42 weeks')
    ], render_kw={'placeholder': 'Current gestational age in weeks', 'class': 'form-control', 'min': '1', 'max': '42'})
    
    submit = SubmitField('Save Patient', render_kw={'class': 'btn btn-primary'})
    
    def validate_date_of_birth(self, field):
        """Validate that date of birth is realistic."""
        if field.data:
            today = date.today()
            min_date = today - timedelta(days=365 * 60)  # 60 years ago
            max_date = today - timedelta(days=365 * 12)  # 12 years ago (minimum pregnancy age)
            
            if field.data < min_date:
                raise ValidationError('Date of birth cannot be more than 60 years ago.')
            
            if field.data > max_date:
                raise ValidationError('Patient must be at least 12 years old.')
            
            if field.data > today:
                raise ValidationError('Date of birth cannot be in the future.')
    
    def validate_national_id(self, field):
        """Check if national ID already exists (if provided)."""
        if field.data and field.data.strip():
            # Only check for duplicates if this is a new patient or if the ID changed
            existing_patient = Patient.query.filter_by(national_id=field.data.strip()).first()
            if existing_patient:
                # If we're editing and it's the same patient, allow it
                if not hasattr(self, 'patient_id') or existing_patient.id != getattr(self, 'patient_id', None):
                    raise ValidationError('A patient with this National ID already exists.')


class PatientSearchForm(FlaskForm):
    """Form for searching patients."""
    
    search_query = StringField('Search Patients', validators=[
        Optional(),
        Length(max=100, message='Search query must be less than 100 characters')
    ], render_kw={
        'placeholder': 'Search by name, phone, or National ID...', 
        'class': 'form-control',
        'autocomplete': 'off'
    })
    
    search_submit = SubmitField('Search', render_kw={'class': 'btn btn-outline-primary'})


class ClinicalMetricsForm(FlaskForm):
    """Form for adding/editing clinical metrics."""
    
    visit_date = DateField('Visit Date', validators=[
        DataRequired(message='Visit date is required')
    ], default=date.today, render_kw={'class': 'form-control'})
    
    # Core measurements
    bmi = StringField('BMI (kg/m²)', validators=[
        Optional()
    ], render_kw={'placeholder': 'e.g., 24.5', 'class': 'form-control', 'step': '0.1'})
    
    systolic_bp = IntegerField('Systolic Blood Pressure (mmHg)', validators=[
        Optional(),
        NumberRange(min=70, max=250, message='Systolic BP must be between 70 and 250 mmHg')
    ], render_kw={'placeholder': 'e.g., 120', 'class': 'form-control', 'min': '70', 'max': '250'})
    
    diastolic_bp = IntegerField('Diastolic Blood Pressure (mmHg)', validators=[
        Optional(),
        NumberRange(min=40, max=150, message='Diastolic BP must be between 40 and 150 mmHg')
    ], render_kw={'placeholder': 'e.g., 80', 'class': 'form-control', 'min': '40', 'max': '150'})
    
    # Laboratory values
    hemoglobin = StringField('Hemoglobin (g/dL)', validators=[
        Optional()
    ], render_kw={'placeholder': 'e.g., 12.5', 'class': 'form-control', 'step': '0.1'})
    
    hdl_cholesterol = StringField('HDL Cholesterol (mg/dL)', validators=[
        Optional()
    ], render_kw={'placeholder': 'e.g., 50', 'class': 'form-control'})
    
    pregnancies_count = IntegerField('Total Number of Pregnancies', validators=[
        Optional(),
        NumberRange(min=1, max=20, message='Number of pregnancies must be between 1 and 20')
    ], render_kw={'placeholder': 'Including current pregnancy', 'class': 'form-control', 'min': '1', 'max': '20'})
    
    # Risk factors (boolean choices)
    sedentary_lifestyle = SelectField('Sedentary Lifestyle', choices=[
        ('', 'Select...'),
        ('True', 'Yes'),
        ('False', 'No')
    ], validators=[Optional()], render_kw={'class': 'form-select'})
    
    family_history_diabetes = SelectField('Family History of Diabetes', choices=[
        ('', 'Select...'),
        ('True', 'Yes'),
        ('False', 'No')
    ], validators=[Optional()], render_kw={'class': 'form-select'})
    
    prediabetes_history = SelectField('History of Prediabetes', choices=[
        ('', 'Select...'),
        ('True', 'Yes'),
        ('False', 'No')
    ], validators=[Optional()], render_kw={'class': 'form-select'})
    
    pcos_history = SelectField('History of PCOS', choices=[
        ('', 'Select...'),
        ('True', 'Yes'),
        ('False', 'No')
    ], validators=[Optional()], render_kw={'class': 'form-select'})
    
    previous_gdm = SelectField('Previous Gestational Diabetes', choices=[
        ('', 'Select...'),
        ('True', 'Yes'),
        ('False', 'No')
    ], validators=[Optional()], render_kw={'class': 'form-select'})
    
    previous_macrosomia = SelectField('Previous Baby > 4kg', choices=[
        ('', 'Select...'),
        ('True', 'Yes'),
        ('False', 'No')
    ], validators=[Optional()], render_kw={'class': 'form-select'})
    
    notes = TextAreaField('Clinical Notes', validators=[
        Optional(),
        Length(max=1000, message='Notes must be less than 1000 characters')
    ], render_kw={
        'placeholder': 'Additional clinical observations or notes...', 
        'class': 'form-control',
        'rows': '3'
    })
    
    submit = SubmitField('Save Clinical Metrics', render_kw={'class': 'btn btn-success'})
    
    def validate_visit_date(self, field):
        """Validate visit date is not in the future."""
        if field.data and field.data > date.today():
            raise ValidationError('Visit date cannot be in the future.')
    
    def validate_bmi(self, field):
        """Validate BMI is a valid float."""
        if field.data and field.data.strip():
            try:
                bmi_value = float(field.data)
                if bmi_value < 10 or bmi_value > 60:
                    raise ValidationError('BMI must be between 10 and 60.')
            except ValueError:
                raise ValidationError('BMI must be a valid number.')
    
    def validate_hemoglobin(self, field):
        """Validate hemoglobin is a valid float."""
        if field.data and field.data.strip():
            try:
                hgb_value = float(field.data)
                if hgb_value < 5 or hgb_value > 20:
                    raise ValidationError('Hemoglobin must be between 5 and 20 g/dL.')
            except ValueError:
                raise ValidationError('Hemoglobin must be a valid number.')
    
    def validate_hdl_cholesterol(self, field):
        """Validate HDL cholesterol is a valid integer."""
        if field.data and field.data.strip():
            try:
                hdl_value = int(field.data)
                if hdl_value < 10 or hdl_value > 200:
                    raise ValidationError('HDL cholesterol must be between 10 and 200 mg/dL.')
            except ValueError:
                raise ValidationError('HDL cholesterol must be a valid number.')
    
    def get_processed_data(self):
        """Get form data with proper type conversion."""
        data = {}
        
        # Date field
        if self.visit_date.data:
            data['visit_date'] = self.visit_date.data
        
        # Float fields
        if self.bmi.data and self.bmi.data.strip():
            data['bmi'] = float(self.bmi.data)
        
        if self.hemoglobin.data and self.hemoglobin.data.strip():
            data['hemoglobin'] = float(self.hemoglobin.data)
        
        if self.hdl_cholesterol.data and self.hdl_cholesterol.data.strip():
            data['hdl_cholesterol'] = int(self.hdl_cholesterol.data)
        
        # Integer fields
        if self.systolic_bp.data:
            data['systolic_bp'] = self.systolic_bp.data
        
        if self.diastolic_bp.data:
            data['diastolic_bp'] = self.diastolic_bp.data
        
        if self.pregnancies_count.data:
            data['pregnancies_count'] = self.pregnancies_count.data
        
        # Boolean fields
        boolean_fields = [
            'sedentary_lifestyle', 'family_history_diabetes', 'prediabetes_history',
            'pcos_history', 'previous_gdm', 'previous_macrosomia'
        ]
        
        for field_name in boolean_fields:
            field_value = getattr(self, field_name).data
            if field_value and field_value.strip():
                data[field_name] = field_value == 'True'
        
        # Text field
        if self.notes.data and self.notes.data.strip():
            data['notes'] = self.notes.data.strip()
        
        return data