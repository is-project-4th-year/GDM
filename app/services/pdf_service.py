"""
PDF Generation Service for GDM Risk Assessment Reports - Windows Compatible
Using ReportLab instead of WeasyPrint for better Windows compatibility
"""
import os
import uuid
from datetime import datetime
from pathlib import Path
from flask import current_app

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from app.models.audit_log import AuditLog, AuditAction


class PDFReportService:
    """Service for generating PDF reports from risk assessments using ReportLab."""
    
    def __init__(self):
        self.reports_dir = self._ensure_reports_directory()
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _ensure_reports_directory(self):
        """Ensure the reports directory exists."""
        reports_path = Path(current_app.root_path) / 'static' / 'reports'
        reports_path.mkdir(parents=True, exist_ok=True)
        return reports_path
    
    def _setup_custom_styles(self):
        """Set up custom styles for the PDF."""
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            textColor=colors.darkblue,
            alignment=1  # Center
        )
        
        self.heading_style = ParagraphStyle(
            'CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            textColor=colors.darkblue
        )
        
        self.normal_style = ParagraphStyle(
            'CustomNormal',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=6
        )
    
    def generate_risk_assessment_report(self, risk_assessment, user_id, include_recommendations=True):
        """
        Generate a comprehensive PDF report for a risk assessment.
        
        Args:
            risk_assessment: RiskAssessment object
            user_id: ID of the user generating the report
            include_recommendations: Whether to include clinical recommendations
            
        Returns:
            Report object with PDF path information
        """
        try:
            from app import db
            from app.models.report import Report
            
            # Use assessment creation time or current time for header
            generated_at = risk_assessment.created_at or datetime.utcnow()
            
            # Generate unique filename
            filename = f"gdm_report_{risk_assessment.patient.uuid}_{uuid.uuid4().hex[:8]}.pdf"
            pdf_path = self.reports_dir / filename
            
            # Create PDF document
            doc = SimpleDocTemplate(
                str(pdf_path),
                pagesize=A4,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=72
            )
            
            # Build the document content
            story = []
            
            # Add header
            self._add_header(story, generated_at)
            
            # Add patient information
            self._add_patient_info(story, risk_assessment)
            
            # Add risk assessment results
            self._add_risk_results(story, risk_assessment)
            
            # Add clinical data
            self._add_clinical_data(story, risk_assessment)
            
            # Add recommendations if requested
            if include_recommendations:
                self._add_recommendations(story, risk_assessment)
            
            # Add disclaimer
            self._add_disclaimer(story)
            
            # Build PDF
            doc.build(story)
            
            # Get file size
            file_size = pdf_path.stat().st_size
            
            # Create report record in database
            report_title = f"GDM Risk Assessment - {risk_assessment.patient.full_name}"
            summary = self._generate_report_summary(risk_assessment)
            
            report = Report.create_report(
                patient_id=risk_assessment.patient_id,
                risk_assessment_id=risk_assessment.id,
                generated_by=user_id,
                title=report_title,
                summary_text=summary
            )
            
            report.pdf_filename = filename
            report.pdf_path = str(pdf_path)
            report.file_size = file_size
            
            # Save to database
            db.session.add(report)
            db.session.commit()
            
            # Log the action
            AuditLog.log_action(
                action=AuditAction.GENERATE_REPORT,
                user_id=user_id,
                entity="report",
                entity_id=report.id,
                details=f"Generated PDF report for patient: {risk_assessment.patient.full_name}"
            )
            
            return report
            
        except Exception as e:
            if 'db' in locals():
                db.session.rollback()
            current_app.logger.error(f"PDF generation failed: {str(e)}")
            raise Exception(f"Failed to generate PDF report: {str(e)}")
    
    def _add_header(self, story, generated_at):
        """Add report header."""
        generated_at_str = generated_at.strftime('%B %d, %Y at %I:%M %p')
        
        header_text = (
            '<para align="center">'
            '<b>GDM Risk Prediction System</b><br/>'
            'Gestational Diabetes Mellitus Risk Assessment Report<br/>'
            f'<i>Generated on {generated_at_str}</i>'
            '</para>'
        )
        
        story.append(Paragraph(header_text, self.title_style))
        story.append(Spacer(1, 20))
    
    def _add_patient_info(self, story, assessment):
        """Add patient information section."""
        story.append(Paragraph("Patient Information", self.heading_style))
        
        patient = assessment.patient
        
        # Create patient info table
        data = [
            ['Full Name:', patient.full_name],
            ['Patient ID:', patient.uuid],
            ['Date of Birth:', patient.date_of_birth.strftime('%B %d, %Y')],
            ['Age:', f"{patient.age} years"],
            ['Assessment Date:', assessment.created_at.strftime('%B %d, %Y at %I:%M %p')],
        ]
        
        if patient.phone:
            data.append(['Phone:', patient.phone])
        if patient.national_id:
            data.append(['National ID:', patient.national_id])
        
        table = Table(data, colWidths=[2*inch, 4*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        
        story.append(table)
        story.append(Spacer(1, 20))
    
    def _add_risk_results(self, story, assessment):
        """Add risk assessment results section."""
        story.append(Paragraph("Risk Assessment Results", self.heading_style))
        
        # Risk score display
        risk_percent = assessment.risk_score * 100
        risk_level = self._get_risk_level(assessment.risk_score)
        
        risk_color = (
            colors.green if risk_level == "Low"
            else colors.orange if risk_level == "Moderate"
            else colors.red
        )
        
        risk_text = (
            '<para align="center">'
            f'<b><font size="16" color="{risk_color.hexval()}">'
            f'Risk Score: {risk_percent:.1f}%'
            '</font></b><br/>'
            f'<b><font size="14" color="{risk_color.hexval()}">'
            f'{risk_level} Risk'
            '</font></b><br/>'
            f'{self._get_risk_description(risk_level)}'
            '</para>'
        )
        
        story.append(Paragraph(risk_text, self.normal_style))
        story.append(Spacer(1, 20))
    
    def _add_clinical_data(self, story, assessment):
        """Add clinical data section."""
        story.append(Paragraph("Clinical Data Used for Assessment", self.heading_style))
        
        # Parse input data
        input_data = self._get_input_data(assessment)
        
        if input_data:
            data = [
                ['Parameter', 'Value', 'Reference Range'],
                ['Age', f"{input_data.get('age', 'N/A')} years", 'N/A'],
                ['BMI', f"{input_data.get('bmi', 'N/A')}", '<25 Normal, 25-29.9 Overweight, ≥30 Obese'],
                ['Systolic BP', f"{input_data.get('sys_bp', 'N/A')} mmHg", '<140 mmHg'],
                ['Diastolic BP', f"{input_data.get('dia_bp', 'N/A')} mmHg", '<90 mmHg'],
                ['Hemoglobin', f"{input_data.get('hemoglobin', 'N/A')} g/dL", '11.0-15.0 g/dL'],
                ['HDL', f"{input_data.get('hdl', 'N/A')} mg/dL", '>40 mg/dL'],
                ['Pregnancies', f"{input_data.get('pregnancies', 'N/A')}", 'N/A'],
                ['Family History DM', 'Yes' if input_data.get('family_history_dm') else 'No', 'N/A'],
                ['Sedentary Lifestyle', 'Yes' if input_data.get('sedentary_lifestyle') else 'No', 'N/A'],
                ['Prediabetes', 'Yes' if input_data.get('prediabetes') else 'No', 'N/A'],
            ]
            
            table = Table(data, colWidths=[2*inch, 1.5*inch, 2.5*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            
            story.append(table)
        else:
            story.append(Paragraph("Clinical data not available for display.", self.normal_style))
        
        story.append(Spacer(1, 20))
    
    def _add_recommendations(self, story, assessment):
        """Add clinical recommendations section."""
        story.append(Paragraph("Clinical Recommendations", self.heading_style))
        
        recommendations = self._generate_clinical_recommendations(assessment)
        
        if recommendations:
            rec_text = "<b>Recommended Actions:</b><br/><br/>"
            for i, rec in enumerate(recommendations, 1):
                rec_text += f"{i}. {rec}<br/>"
            
            story.append(Paragraph(rec_text, self.normal_style))
            
            disclaimer = (
                "<br/><b>Note:</b> These recommendations are generated based on the risk assessment "
                "results and should be reviewed by a qualified healthcare provider. Individual "
                "patient circumstances may require modified approaches."
            )
            story.append(Paragraph(disclaimer, self.normal_style))
        
        story.append(Spacer(1, 20))
    
    def _add_disclaimer(self, story):
        """Add important disclaimer."""
        disclaimer_text = (
            "<para>"
            "<b>Important Disclaimer</b><br/>"
            "This risk assessment is for clinical decision support only and should not replace "
            "clinical judgment. The results are based on statistical models and population data. "
            "Individual patient factors not captured in this assessment may significantly impact "
            "actual risk. Always consult with qualified healthcare providers for diagnosis and "
            "treatment decisions. This assessment does not constitute medical advice, diagnosis, "
            "or treatment recommendation."
            "</para>"
        )
        
        style = ParagraphStyle(
            'Disclaimer',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.grey
        )
        
        story.append(Paragraph(disclaimer_text, style))
    
    def _get_risk_level(self, risk_score):
        """Get risk level from score."""
        if risk_score <= 0.33:
            return "Low"
        elif risk_score <= 0.66:
            return "Moderate"
        else:
            return "High"
    
    def _get_risk_description(self, risk_level):
        """Get risk description."""
        descriptions = {
            "Low": "Patient has a low risk of developing gestational diabetes mellitus.",
            "Moderate": "Patient has a moderate risk of developing gestational diabetes mellitus.",
            "High": "Patient has a high risk of developing gestational diabetes mellitus."
        }
        return descriptions.get(risk_level, "")
    
    def _get_input_data(self, assessment):
        """Extract and format input data."""
        if hasattr(assessment, 'input_vector_json') and assessment.input_vector_json:
            try:
                import json
                return json.loads(assessment.input_vector_json)
            except:
                return {}
        return {}
    
    def _generate_clinical_recommendations(self, assessment):
        """Generate clinical recommendations based on assessment."""
        recommendations = []
        risk_score = assessment.risk_score
        
        if risk_score > 0.66:  # High risk
            recommendations.extend([
                "Immediate glucose tolerance testing",
                "Nutritional counseling with registered dietitian",
                "Increased frequency of prenatal visits",
                "Self-monitoring of blood glucose if indicated",
                "Weight management guidance",
                "Exercise program development (as appropriate)",
            ])
        elif risk_score > 0.33:  # Moderate risk
            recommendations.extend([
                "Early glucose screening at 24-28 weeks",
                "Lifestyle modification counseling", 
                "Weight monitoring throughout pregnancy",
                "Nutritional guidance for healthy pregnancy weight gain",
            ])
        else:  # Low risk
            recommendations.extend([
                "Standard glucose screening at 24-28 weeks",
                "Continue current healthy lifestyle habits",
                "Routine prenatal monitoring",
            ])
        
        return recommendations
    
    def _generate_report_summary(self, assessment):
        """Generate a brief summary."""
        risk_level = self._get_risk_level(assessment.risk_score)
        risk_percentage = assessment.risk_score * 100
        return f"GDM Risk Assessment: {risk_level} risk ({risk_percentage:.1f}%) - Patient {assessment.patient.full_name}"
    
    def delete_report_file(self, report):
        """Delete the PDF file associated with a report."""
        if report.pdf_path and os.path.exists(report.pdf_path):
            try:
                os.remove(report.pdf_path)
                return True
            except OSError:
                return False
        return False
    
    def _prepare_report_data(self, risk_assessment, include_recommendations=True):
        """Prepare data for preview (compatibility method)."""
        patient = risk_assessment.patient
        
        # Calculate age at assessment
        age_at_assessment = patient.age
        
        # Get latest clinical metrics
        latest_metrics = patient.latest_clinical_metrics
        
        # Risk level interpretation
        risk_interpretation = {
            'level': f"{self._get_risk_level(risk_assessment.risk_score)} Risk",
            'description': self._get_risk_description(self._get_risk_level(risk_assessment.risk_score)),
            'follow_up': "Please consult with healthcare provider for appropriate follow-up."
        }
        
        # Clinical recommendations
        recommendations = []
        if include_recommendations:
            recommendations = self._generate_clinical_recommendations(risk_assessment)
        
        # Format input data
        input_data = self._get_input_data(risk_assessment)
        if input_data:
            formatted_data = {
                'age': input_data.get('age', 'N/A'),
                'bmi': f"{input_data.get('bmi', 'N/A'):.1f}" if input_data.get('bmi') else 'N/A',
                'systolic_bp': f"{input_data.get('sys_bp', 'N/A')} mmHg" if input_data.get('sys_bp') else 'N/A',
                'diastolic_bp': f"{input_data.get('dia_bp', 'N/A')} mmHg" if input_data.get('dia_bp') else 'N/A',
                'hemoglobin': f"{input_data.get('hemoglobin', 'N/A')} g/dL" if input_data.get('hemoglobin') else 'N/A',
                'hdl': f"{input_data.get('hdl', 'N/A')} mg/dL" if input_data.get('hdl') else 'N/A',
                'pregnancies': input_data.get('pregnancies', 'N/A'),
                'family_history': 'Yes' if input_data.get('family_history_dm', False) else 'No',
                'sedentary_lifestyle': 'Yes' if input_data.get('sedentary_lifestyle', False) else 'No',
                'prediabetes': 'Yes' if input_data.get('prediabetes', False) else 'No',
            }
        else:
            formatted_data = {}
        
        return {
            'patient': patient,
            'risk_assessment': risk_assessment,
            'latest_metrics': latest_metrics,
            'age_at_assessment': age_at_assessment,
            'risk_interpretation': risk_interpretation,
            'recommendations': recommendations,
            'input_data': formatted_data,
            'include_recommendations': include_recommendations
        }
