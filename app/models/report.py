import os
from datetime import datetime
from app import db


class Report(db.Model):
    """Report model for storing generated PDF reports and summaries."""
    
    __tablename__ = 'reports'
    
    # Primary key
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign keys
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    risk_assessment_id = db.Column(db.Integer, db.ForeignKey('risk_assessments.id'), nullable=False)
    
    # Report content
    pdf_path = db.Column(db.String(255), nullable=True)  # Path to generated PDF file
    summary_text = db.Column(db.Text, nullable=False)  # Text summary of the assessment
    
    # System fields
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    risk_assessment = db.relationship('RiskAssessment', backref='reports')
    
    def __init__(self, patient_id, risk_assessment_id, summary_text, pdf_path=None):
        """Initialize report."""
        self.patient_id = patient_id
        self.risk_assessment_id = risk_assessment_id
        self.summary_text = summary_text
        self.pdf_path = pdf_path
    
    @property
    def filename(self):
        """Get the filename of the PDF report."""
        if self.pdf_path:
            return os.path.basename(self.pdf_path)
        return None
    
    @property
    def file_exists(self):
        """Check if the PDF file exists on disk."""
        if not self.pdf_path:
            return False
        return os.path.exists(self.pdf_path)
    
    @property
    def file_size_mb(self):
        """Get file size in megabytes."""
        if not self.file_exists:
            return 0
        try:
            size_bytes = os.path.getsize(self.pdf_path)
            return round(size_bytes / (1024 * 1024), 2)
        except OSError:
            return 0
    
    def generate_summary(self):
        """Generate a comprehensive summary of the risk assessment."""
        assessment = self.risk_assessment
        patient = assessment.patient
        
        summary_parts = []
        
        # Patient information
        summary_parts.append(f"GESTATIONAL DIABETES RISK ASSESSMENT REPORT")
        summary_parts.append(f"Patient: {patient.full_name}")
        summary_parts.append(f"Date of Birth: {patient.date_of_birth.strftime('%B %d, %Y')}")
        summary_parts.append(f"Age: {patient.age} years")
        summary_parts.append(f"Assessment Date: {assessment.created_at.strftime('%B %d, %Y at %I:%M %p')}")
        summary_parts.append(f"Assessed by: {assessment.assessor.name}")
        summary_parts.append("")
        
        # Risk assessment results
        summary_parts.append("RISK ASSESSMENT RESULTS")
        summary_parts.append(f"Risk Score: {assessment.risk_percentage}%")
        summary_parts.append(f"Risk Level: {assessment.risk_label}")
        summary_parts.append(f"Risk Description: {assessment.risk_description}")
        summary_parts.append("")
        
        # Input parameters
        input_vector = assessment.input_vector
        summary_parts.append("CLINICAL PARAMETERS USED")
        
        if input_vector.get('age'):
            summary_parts.append(f"Age: {input_vector['age']} years")
        if input_vector.get('bmi'):
            summary_parts.append(f"BMI: {input_vector['bmi']} kg/m²")
        if input_vector.get('systolic_bp') and input_vector.get('diastolic_bp'):
            summary_parts.append(f"Blood Pressure: {input_vector['systolic_bp']}/{input_vector['diastolic_bp']} mmHg")
        if input_vector.get('hemoglobin'):
            summary_parts.append(f"Hemoglobin: {input_vector['hemoglobin']} g/dL")
        if input_vector.get('hdl_cholesterol'):
            summary_parts.append(f"HDL Cholesterol: {input_vector['hdl_cholesterol']} mg/dL")
        if input_vector.get('pregnancies_count') is not None:
            summary_parts.append(f"Number of Pregnancies: {input_vector['pregnancies_count']}")
        
        # Risk factors
        summary_parts.append("")
        summary_parts.append("RISK FACTORS")
        risk_factors = []
        if input_vector.get('family_history_diabetes'):
            risk_factors.append("Family history of diabetes")
        if input_vector.get('sedentary_lifestyle'):
            risk_factors.append("Sedentary lifestyle")
        if input_vector.get('prediabetes_history'):
            risk_factors.append("History of prediabetes")
        
        if risk_factors:
            for factor in risk_factors:
                summary_parts.append(f"• {factor}")
        else:
            summary_parts.append("No significant risk factors identified from assessed parameters.")
        
        # Recommendations
        summary_parts.append("")
        summary_parts.append("CLINICAL RECOMMENDATIONS")
        for i, recommendation in enumerate(assessment.recommendations, 1):
            summary_parts.append(f"{i}. {recommendation}")
        
        # Footer
        summary_parts.append("")
        summary_parts.append("IMPORTANT NOTES")
        summary_parts.append("• This assessment is based on machine learning prediction and should be used")
        summary_parts.append("  as a clinical decision support tool, not as a definitive diagnosis.")
        summary_parts.append("• Follow-up glucose testing and clinical evaluation are recommended")
        summary_parts.append("  based on standard clinical guidelines.")
        summary_parts.append("• Consult with healthcare provider for comprehensive care planning.")
        summary_parts.append("")        
        summary_parts.append(f"Model Version: {assessment.model_version}")
        summary_parts.append(f"Report Generated: {self.created_at.strftime('%B %d, %Y at %I:%M %p')}")
        
        return "\n".join(summary_parts)
    
    def set_pdf_path(self, pdf_path):
        """Set the PDF file path after generation."""
        self.pdf_path = pdf_path
    
    def delete_pdf_file(self):
        """Delete the associated PDF file from disk."""
        if self.pdf_path and os.path.exists(self.pdf_path):
            try:
                os.remove(self.pdf_path)
                return True
            except OSError:
                return False
        return False
    
    def to_dict(self):
        """Convert report to dictionary."""
        return {
            'id': self.id,
            'patient_id': self.patient_id,
            'risk_assessment_id': self.risk_assessment_id,
            'filename': self.filename,
            'file_exists': self.file_exists,
            'file_size_mb': self.file_size_mb,
            'summary_text': self.summary_text,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def get_recent_reports(cls, limit=20):
        """Get recently generated reports."""
        return cls.query.order_by(cls.created_at.desc()).limit(limit).all()
    
    @classmethod
    def get_reports_for_patient(cls, patient_id):
        """Get all reports for a specific patient."""
        return cls.query.filter_by(patient_id=patient_id).order_by(cls.created_at.desc()).all()
    
    @classmethod
    def cleanup_orphaned_files(cls, reports_directory):
        """Clean up PDF files that no longer have corresponding database records."""
        if not os.path.exists(reports_directory):
            return 0
        
        # Get all PDF files in the reports directory
        pdf_files = [f for f in os.listdir(reports_directory) if f.endswith('.pdf')]
        
        # Get all PDF paths from database
        db_paths = [report.pdf_path for report in cls.query.all() if report.pdf_path]
        db_filenames = [os.path.basename(path) for path in db_paths]
        
        # Find orphaned files
        orphaned_files = [f for f in pdf_files if f not in db_filenames]
        
        # Delete orphaned files
        deleted_count = 0
        for filename in orphaned_files:
            file_path = os.path.join(reports_directory, filename)
            try:
                os.remove(file_path)
                deleted_count += 1
            except OSError:
                continue
        
        return deleted_count
    
    def __repr__(self):
        """String representation of report."""
        return f'<Report Patient:{self.patient_id} Assessment:{self.risk_assessment_id}>'