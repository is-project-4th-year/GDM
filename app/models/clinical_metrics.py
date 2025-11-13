from datetime import datetime, date
from app import db


class ClinicalMetrics(db.Model):
    """Clinical metrics model for storing patient measurements and health indicators."""
    
    __tablename__ = 'clinical_metrics'
    
    # Primary key
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign key to patient
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    
    # Visit information
    visit_date = db.Column(db.Date, nullable=False, default=date.today)
    
    # Core measurements (required for ML prediction)
    bmi = db.Column(db.Float, nullable=True)  # Body Mass Index
    systolic_bp = db.Column(db.Integer, nullable=True)  # Systolic Blood Pressure
    diastolic_bp = db.Column(db.Integer, nullable=True)  # Diastolic Blood Pressure
    
    # Laboratory values (optional but important)
    hemoglobin = db.Column(db.Float, nullable=True)  # g/dL
    hdl_cholesterol = db.Column(db.Float, nullable=True)  # mg/dL
    
    # Pregnancy and history information
    pregnancies_count = db.Column(db.Integer, nullable=True)  # Total number of pregnancies
    
    # Risk factors (boolean fields)
    sedentary_lifestyle = db.Column(db.Boolean, nullable=True)  # Sedentary lifestyle
    family_history_diabetes = db.Column(db.Boolean, nullable=True)  # Family history of diabetes
    prediabetes_history = db.Column(db.Boolean, nullable=True)  # History of prediabetes
    
    # Optional risk factors
    pcos_history = db.Column(db.Boolean, nullable=True)  # Polycystic ovary syndrome
    previous_gdm = db.Column(db.Boolean, nullable=True)  # Previous gestational diabetes
    previous_macrosomia = db.Column(db.Boolean, nullable=True)  # Previous baby >4kg
    
    # Additional information
    notes = db.Column(db.Text, nullable=True)  # Clinical notes
    
    # System fields
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __init__(self, patient_id, visit_date=None, **kwargs):
        """Initialize clinical metrics."""
        self.patient_id = patient_id
        self.visit_date = visit_date or date.today()
        
        # Core measurements
        self.bmi = kwargs.get('bmi')
        self.systolic_bp = kwargs.get('systolic_bp')
        self.diastolic_bp = kwargs.get('diastolic_bp')
        
        # Laboratory values
        self.hemoglobin = kwargs.get('hemoglobin')
        self.hdl_cholesterol = kwargs.get('hdl_cholesterol')
        
        # Pregnancy information
        self.pregnancies_count = kwargs.get('pregnancies_count')
        
        # Risk factors
        self.sedentary_lifestyle = kwargs.get('sedentary_lifestyle')
        self.family_history_diabetes = kwargs.get('family_history_diabetes')
        self.prediabetes_history = kwargs.get('prediabetes_history')
        self.pcos_history = kwargs.get('pcos_history')
        self.previous_gdm = kwargs.get('previous_gdm')
        self.previous_macrosomia = kwargs.get('previous_macrosomia')
        
        # Additional information
        self.notes = kwargs.get('notes')
    
    @property
    def blood_pressure_category(self):
        """Categorize blood pressure reading."""
        if not self.systolic_bp or not self.diastolic_bp:
            return "Unknown"
        
        sys = self.systolic_bp
        dia = self.diastolic_bp
        
        if sys < 120 and dia < 80:
            return "Normal"
        elif sys < 130 and dia < 80:
            return "Elevated"
        elif (sys >= 130 and sys < 140) or (dia >= 80 and dia < 90):
            return "High Blood Pressure Stage 1"
        elif sys >= 140 or dia >= 90:
            return "High Blood Pressure Stage 2"
        else:
            return "Hypertensive Crisis"
    
    @property
    def bmi_category(self):
        """Categorize BMI reading."""
        if not self.bmi:
            return "Unknown"
        
        if self.bmi < 18.5:
            return "Underweight"
        elif self.bmi < 25:
            return "Normal weight"
        elif self.bmi < 30:
            return "Overweight"
        else:
            return "Obese"
    
    @property
    def risk_factor_count(self):
        """Count the number of positive risk factors."""
        risk_factors = [
            self.sedentary_lifestyle,
            self.family_history_diabetes,
            self.prediabetes_history,
            self.pcos_history,
            self.previous_gdm,
            self.previous_macrosomia
        ]
        return sum(1 for factor in risk_factors if factor is True)
    
    def get_ml_input_vector(self):
        """
        Get input vector for ML model prediction.
        Returns dictionary with the 10 core features needed for GDM prediction.
        """
        # Calculate age from patient's date of birth
        patient_age = self.patient.age if self.patient else None
        
        return {
            'age': patient_age,
            'bmi': self.bmi,
            'systolic_bp': self.systolic_bp,
            'diastolic_bp': self.diastolic_bp,
            'hemoglobin': self.hemoglobin,
            'hdl_cholesterol': self.hdl_cholesterol,
            'pregnancies_count': self.pregnancies_count,
            'family_history_diabetes': 1 if self.family_history_diabetes else 0,
            'sedentary_lifestyle': 1 if self.sedentary_lifestyle else 0,
            'prediabetes_history': 1 if self.prediabetes_history else 0
        }
    
    def is_complete_for_prediction(self):
        """Check if metrics are complete enough for ML prediction."""
        required_fields = [
            'bmi', 'systolic_bp', 'diastolic_bp', 'pregnancies_count',
            'family_history_diabetes', 'sedentary_lifestyle', 'prediabetes_history'
        ]
        
        for field in required_fields:
            value = getattr(self, field)
            if value is None:
                return False
        
        return True
    
    def to_dict(self):
        """Convert clinical metrics to dictionary."""
        return {
            'id': self.id,
            'patient_id': self.patient_id,
            'visit_date': self.visit_date.isoformat() if self.visit_date else None,
            'bmi': self.bmi,
            'bmi_category': self.bmi_category,
            'systolic_bp': self.systolic_bp,
            'diastolic_bp': self.diastolic_bp,
            'blood_pressure_category': self.blood_pressure_category,
            'hemoglobin': self.hemoglobin,
            'hdl_cholesterol': self.hdl_cholesterol,
            'pregnancies_count': self.pregnancies_count,
            'sedentary_lifestyle': self.sedentary_lifestyle,
            'family_history_diabetes': self.family_history_diabetes,
            'prediabetes_history': self.prediabetes_history,
            'pcos_history': self.pcos_history,
            'previous_gdm': self.previous_gdm,
            'previous_macrosomia': self.previous_macrosomia,
            'risk_factor_count': self.risk_factor_count,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_complete_for_prediction': self.is_complete_for_prediction()
        }
    
    def __repr__(self):
        """String representation of clinical metrics."""
        return f'<ClinicalMetrics Patient:{self.patient_id} Date:{self.visit_date}>'