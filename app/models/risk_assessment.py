import json
from datetime import datetime
from app import db


class RiskAssessment(db.Model):
    """Risk assessment model for storing GDM prediction results."""
    
    __tablename__ = 'risk_assessments'
    
    # Primary key
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign keys
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    assessed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # ML Model inputs and outputs
    input_vector_json = db.Column(db.Text, nullable=False)  # JSON string of input features
    risk_score = db.Column(db.Float, nullable=False)  # Model prediction score (0-1)
    risk_label = db.Column(db.String(20), nullable=False)  # LOW, MODERATE, HIGH
    model_version = db.Column(db.String(20), nullable=False)  # Version of ML model used
    
    # System fields
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    assessor = db.relationship('User', backref='risk_assessments')
    
    def __init__(self, patient_id, assessed_by, input_vector, risk_score, model_version):
        """Initialize risk assessment."""
        self.patient_id = patient_id
        self.assessed_by = assessed_by
        self.input_vector_json = json.dumps(input_vector)
        self.risk_score = float(risk_score)
        self.model_version = model_version
        self.risk_label = self._calculate_risk_label(risk_score)
    
    @property
    def input_vector(self):
        """Get input vector as dictionary."""
        try:
            return json.loads(self.input_vector_json)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    @property
    def risk_percentage(self):
        """Get risk score as percentage."""
        return round(self.risk_score * 100, 1)
    
    @property
    def risk_color(self):
        """Get color code for risk level."""
        risk_colors = {
            'LOW': 'success',
            'MODERATE': 'warning', 
            'HIGH': 'danger'
        }
        return risk_colors.get(self.risk_label, 'secondary')
    
    @property
    def risk_description(self):
        """Get human-readable risk description."""
        descriptions = {
            'LOW': 'Low risk of developing gestational diabetes',
            'MODERATE': 'Moderate risk of developing gestational diabetes',
            'HIGH': 'High risk of developing gestational diabetes'
        }
        return descriptions.get(self.risk_label, 'Unknown risk level')
    
    @property
    def recommendations(self):
        """Get clinical recommendations based on risk level."""
        if self.risk_label == 'LOW':
            return [
                "Continue routine prenatal care",
                "Maintain healthy diet and regular exercise",
                "Monitor weight gain during pregnancy",
                "Follow standard glucose screening schedule"
            ]
        elif self.risk_label == 'MODERATE':
            return [
                "Enhanced dietary counseling recommended",
                "Increased physical activity as appropriate",
                "Consider earlier glucose screening",
                "More frequent monitoring of weight gain",
                "Discuss family history and risk factors"
            ]
        else:  # HIGH
            return [
                "Immediate dietary consultation recommended",
                "Consider early glucose tolerance testing",
                "Enhanced prenatal monitoring",
                "Lifestyle intervention program enrollment",
                "Close collaboration with endocrinology if needed",
                "Weekly weight monitoring"
            ]
    
    def _calculate_risk_label(self, risk_score):
        """Calculate risk label based on score and thresholds."""
        # These thresholds should match those in config
        if risk_score < 0.33:
            return 'LOW'
        elif risk_score < 0.66:
            return 'MODERATE'
        else:
            return 'HIGH'
    
    def to_dict(self):
        """Convert risk assessment to dictionary."""
        return {
            'id': self.id,
            'patient_id': self.patient_id,
            'assessed_by': self.assessed_by,
            'assessor_name': self.assessor.name if self.assessor else 'Unknown',
            'input_vector': self.input_vector,
            'risk_score': self.risk_score,
            'risk_percentage': self.risk_percentage,
            'risk_label': self.risk_label,
            'risk_color': self.risk_color,
            'risk_description': self.risk_description,
            'recommendations': self.recommendations,
            'model_version': self.model_version,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def get_latest_for_patient(cls, patient_id):
        """Get the most recent risk assessment for a patient."""
        return cls.query.filter_by(patient_id=patient_id).order_by(cls.created_at.desc()).first()
    
    @classmethod
    def get_assessments_by_risk_level(cls, risk_label, limit=None):
        """Get assessments filtered by risk level."""
        query = cls.query.filter_by(risk_label=risk_label).order_by(cls.created_at.desc())
        if limit:
            query = query.limit(limit)
        return query.all()
    
    @classmethod
    def get_recent_assessments(cls, days=30, limit=50):
        """Get recent assessments within specified days."""
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        return cls.query.filter(cls.created_at >= cutoff_date).order_by(cls.created_at.desc()).limit(limit).all()
    
    @classmethod
    def get_statistics(cls):
        """Get overall statistics for risk assessments."""
        total_assessments = cls.query.count()
        
        if total_assessments == 0:
            return {
                'total_assessments': 0,
                'low_risk': 0,
                'moderate_risk': 0,
                'high_risk': 0,
                'low_percentage': 0,
                'moderate_percentage': 0,
                'high_percentage': 0
            }
        
        low_count = cls.query.filter_by(risk_label='LOW').count()
        moderate_count = cls.query.filter_by(risk_label='MODERATE').count()
        high_count = cls.query.filter_by(risk_label='HIGH').count()
        
        return {
            'total_assessments': total_assessments,
            'low_risk': low_count,
            'moderate_risk': moderate_count,
            'high_risk': high_count,
            'low_percentage': round((low_count / total_assessments) * 100, 1),
            'moderate_percentage': round((moderate_count / total_assessments) * 100, 1),
            'high_percentage': round((high_count / total_assessments) * 100, 1)
        }
    
    def __repr__(self):
        """String representation of risk assessment."""
        return f'<RiskAssessment Patient:{self.patient_id} Risk:{self.risk_label} Score:{self.risk_percentage}%>'