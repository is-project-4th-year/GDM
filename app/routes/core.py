from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from app.models import Patient, RiskAssessment, User
from app import db
import json  # Add this import

core_bp = Blueprint('core', __name__)


@core_bp.route('/')
def index():
    """Landing page (public)."""
    return render_template('index.html')


@core_bp.route('/health')
def health():
    """Health check endpoint (public)."""
    return jsonify({
        'status': 'ok', 
        'message': 'GDM Risk Prediction App is running',
        'authenticated': current_user.is_authenticated if hasattr(current_user, 'is_authenticated') else False
    })


@core_bp.route('/dashboard')
@login_required
def dashboard():
    """Enhanced dashboard with KPIs and chart data."""
    try:
        # Calculate KPI statistics
        total_patients = Patient.query.count()
        total_assessments = RiskAssessment.query.count()
        
        # High risk patients count (risk_score > 0.5 indicates high risk)
        high_risk_count = RiskAssessment.query.filter(
            RiskAssessment.risk_score > 0.5
        ).count()
        
        # Assessments this week
        week_start = datetime.utcnow() - timedelta(days=7)
        assessments_this_week = RiskAssessment.query.filter(
            RiskAssessment.created_at >= week_start
        ).count()
        
        # Risk distribution for pie chart
        # Assuming: risk_score 0-0.33 = LOW, 0.33-0.66 = MODERATE, 0.66+ = HIGH
        low_risk = RiskAssessment.query.filter(
            RiskAssessment.risk_score <= 0.33
        ).count()
        
        moderate_risk = RiskAssessment.query.filter(
            RiskAssessment.risk_score > 0.33,
            RiskAssessment.risk_score <= 0.66
        ).count()
        
        high_risk_chart = RiskAssessment.query.filter(
            RiskAssessment.risk_score > 0.66
        ).count()
        
        # Assessment trends for line chart (last 7 days)
        trends = []
        labels = []
        for i in range(6, -1, -1):  # 6 days ago to today
            date = datetime.utcnow().date() - timedelta(days=i)
            count = RiskAssessment.query.filter(
                func.date(RiskAssessment.created_at) == date
            ).count()
            trends.append(count)
            labels.append(date.strftime('%a'))  # Mon, Tue, etc.
        
        # Recent assessments for the table
        recent_assessments = RiskAssessment.query\
            .join(Patient)\
            .order_by(desc(RiskAssessment.created_at))\
            .limit(10)\
            .all()
        
        # Prepare data for template
        stats = {
            'total_patients': total_patients,
            'total_assessments': total_assessments,
            'high_risk_count': high_risk_count,
            'assessments_this_week': assessments_this_week,
            'last_backup': '2024-11-14'  # You can implement actual backup tracking
        }
        
        chart_data = {
            'risk_distribution': {
                'low_risk': low_risk,
                'moderate_risk': moderate_risk,
                'high_risk': high_risk_chart
            },
            'assessment_trends': {
                'labels': labels,
                'counts': trends
            }
        }
        
        # Convert chart data to JSON for the template
        chart_data_json = json.dumps(chart_data)
        
        return render_template(
            'dashboard.html',
            stats=stats,
            chart_data=chart_data,
            chart_data_json=chart_data_json,  # Add this for template
            recent_assessments=recent_assessments
        )
        
    except Exception as e:
        # Fallback to basic dashboard if there's any error
        print(f"Dashboard error: {e}")
        fallback_chart_data = {
            'risk_distribution': {'low_risk': 0, 'moderate_risk': 0, 'high_risk': 0}, 
            'assessment_trends': {'labels': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'], 'counts': [0,0,0,0,0,0,0]}
        }
        return render_template('dashboard.html', 
                             stats={'total_patients': 0, 'total_assessments': 0, 'high_risk_count': 0, 'assessments_this_week': 0},
                             chart_data=fallback_chart_data,
                             chart_data_json=json.dumps(fallback_chart_data),
                             recent_assessments=[])