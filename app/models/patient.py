import uuid
from datetime import datetime, date
from app import db
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import String


class Patient(db.Model):
    """Patient model for storing patient demographic and basic information."""
    
    __tablename__ = 'patients'
    
    # Primary key
    id = db.Column(db.Integer, primary_key=True)
    
    # Unique identifier for patient (UUID for privacy/security)
    uuid = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()), index=True)
    
    # Basic demographic information
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)
    
    # Optional fields
    national_id = db.Column(db.String(50), nullable=True, index=True)  # SSN, NHS number, etc.
    phone = db.Column(db.String(20), nullable=True)
    
    # Pregnancy-related information
    parity = db.Column(db.Integer, nullable=True)  # Number of previous pregnancies
    gestational_age_weeks = db.Column(db.Integer, nullable=True)  # Current gestational age
    
    # System fields
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Relationships
    creator = db.relationship('User', backref='created_patients')
    clinical_metrics = db.relationship('ClinicalMetrics', backref='patient', lazy='dynamic', cascade='all, delete-orphan')
    risk_assessments = db.relationship('RiskAssessment', backref='patient', lazy='dynamic', cascade='all, delete-orphan')
    reports = db.relationship('Report', backref='patient', lazy='dynamic', cascade='all, delete-orphan')
    
    def __init__(self, first_name, last_name, date_of_birth, created_by, **kwargs):
        """Initialize patient with required fields."""
        self.first_name = first_name.strip()
        self.last_name = last_name.strip()
        self.date_of_birth = date_of_birth
        self.created_by = created_by
        
        # Optional fields
        self.national_id = kwargs.get('national_id')
        self.phone = kwargs.get('phone')
        self.parity = kwargs.get('parity')
        self.gestational_age_weeks = kwargs.get('gestational_age_weeks')
        
        # Generate UUID if not provided
        if not hasattr(self, 'uuid') or not self.uuid:
            self.uuid = str(uuid.uuid4())
    
    @property
    def full_name(self):
        """Get full name of patient."""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def age(self):
        """Calculate current age of patient."""
        today = date.today()
        return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
    
    @property
    def latest_clinical_metrics(self):
        """Get the most recent clinical metrics for this patient."""
        return self.clinical_metrics.order_by(ClinicalMetrics.visit_date.desc()).first()
    
    @property
    def latest_risk_assessment(self):
        """Get the most recent risk assessment for this patient."""
        return self.risk_assessments.order_by(RiskAssessment.created_at.desc()).first()
    
    @property
    def assessment_count(self):
        """Get total number of risk assessments for this patient."""
        return self.risk_assessments.count()
    
    def get_clinical_metrics_history(self, limit=None):
        """Get clinical metrics history ordered by visit date."""
        query = self.clinical_metrics.order_by(ClinicalMetrics.visit_date.desc())
        if limit:
            query = query.limit(limit)
        return query.all()
    
    def get_risk_assessment_history(self, limit=None):
        """Get risk assessment history ordered by creation date."""
        query = self.risk_assessments.order_by(RiskAssessment.created_at.desc())
        if limit:
            query = query.limit(limit)
        return query.all()
    
    def to_dict(self):
        """Convert patient to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'uuid': self.uuid,
            'full_name': self.full_name,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'date_of_birth': self.date_of_birth.isoformat() if self.date_of_birth else None,
            'age': self.age,
            'phone': self.phone,
            'parity': self.parity,
            'gestational_age_weeks': self.gestational_age_weeks,
            'assessment_count': self.assessment_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_active': self.is_active
        }
    
    def __repr__(self):
        """String representation of patient."""
        return f'<Patient {self.full_name} ({self.uuid})>'
    
    @classmethod
    def search(cls, query, limit=50):
        """Search patients by name, phone, or national ID."""
        search_term = f"%{query.strip()}%"
        return cls.query.filter(
            db.and_(
                cls.is_active == True,
                db.or_(
                    cls.first_name.ilike(search_term),
                    cls.last_name.ilike(search_term),
                    cls.phone.ilike(search_term),
                    cls.national_id.ilike(search_term) if query.strip() else False
                )
            )
        ).limit(limit).all()
    
    @classmethod
    def get_active_patients(cls, limit=None):
        """Get all active patients ordered by creation date."""
        query = cls.query.filter_by(is_active=True).order_by(cls.created_at.desc())
        if limit:
            query = query.limit(limit)
        return query.all()


# Import here to avoid circular imports
from app.models.clinical_metrics import ClinicalMetrics
from app.models.risk_assessment import RiskAssessment
from app.models.report import Report