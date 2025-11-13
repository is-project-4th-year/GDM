import click
from flask import current_app
from flask.cli import with_appcontext
from werkzeug.security import generate_password_hash
from datetime import date, datetime, timedelta
import random

from app import db
from app.models.user import User
from app.models.patient import Patient
from app.models.clinical_metrics import ClinicalMetrics
from app.models.risk_assessment import RiskAssessment
from app.models.audit_log import AuditLog, AuditAction


@click.command()
@click.option('--name', prompt='Admin full name', help='Full name of the admin user')
@click.option('--email', prompt='Admin email', help='Email address for the admin user')
@click.option('--password', prompt=True, hide_input=True, 
              confirmation_prompt=True, help='Password for the admin user')
@with_appcontext
def create_admin(name, email, password):
    """Create an admin user."""
    
    # Check if user already exists
    existing_user = User.query.filter_by(email=email.lower()).first()
    if existing_user:
        click.echo(f'Error: User with email {email} already exists.')
        return
    
    try:
        # Create admin user
        admin = User.create_admin(name=name, email=email, password=password)
        
        # Save to database
        db.session.add(admin)
        db.session.commit()
        
        click.echo(f'✅ Admin user created successfully!')
        click.echo(f'   Name: {admin.name}')
        click.echo(f'   Email: {admin.email}')
        click.echo(f'   Role: {admin.role}')
        click.echo(f'\nYou can now log in at: http://localhost:5000/auth/login')
        
    except Exception as e:
        db.session.rollback()
        click.echo(f'Error creating admin user: {str(e)}')


@click.command()
@with_appcontext
def init_db():
    """Initialize the database."""
    try:
        db.create_all()
        click.echo('✅ Database initialized successfully!')
    except Exception as e:
        click.echo(f'Error initializing database: {str(e)}')


@click.command()
@click.option('--patients', default=5, help='Number of sample patients to create')
@with_appcontext
def seed_data(patients):
    """Seed the database with sample data for testing."""
    
    try:
        # Get the first admin user
        admin = User.query.filter_by(role='admin').first()
        if not admin:
            click.echo('Error: No admin user found. Create an admin user first.')
            return
        
        click.echo(f'Creating {patients} sample patients...')
        
        # Sample patient data
        first_names = ['Sarah', 'Maria', 'Jennifer', 'Lisa', 'Jessica', 'Amanda', 'Michelle', 'Rachel', 'Emily', 'Ashley']
        last_names = ['Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez', 'Hernandez']
        
        created_patients = []
        
        for i in range(patients):
            # Create patient
            patient = Patient(
                first_name=random.choice(first_names),
                last_name=random.choice(last_names),
                date_of_birth=date.today() - timedelta(days=random.randint(7300, 14600)),  # 20-40 years old
                created_by=admin.id,
                phone=f'+1{random.randint(1000000000, 9999999999)}',
                parity=random.randint(0, 3),
                gestational_age_weeks=random.randint(12, 32)
            )
            
            db.session.add(patient)
            db.session.flush()  # Get the patient ID
            
            # Create clinical metrics for the patient
            metrics = ClinicalMetrics(
                patient_id=patient.id,
                visit_date=date.today() - timedelta(days=random.randint(1, 30)),
                bmi=round(random.uniform(18.5, 35.0), 1),
                systolic_bp=random.randint(110, 160),
                diastolic_bp=random.randint(70, 100),
                hemoglobin=round(random.uniform(10.0, 14.0), 1),
                hdl_cholesterol=random.randint(35, 80),
                pregnancies_count=random.randint(1, 4),
                sedentary_lifestyle=random.choice([True, False]),
                family_history_diabetes=random.choice([True, False, False]),  # 33% chance
                prediabetes_history=random.choice([True, False, False, False]),  # 25% chance
                pcos_history=random.choice([True, False, False, False, False]),  # 20% chance
                previous_gdm=random.choice([True, False, False, False, False]),  # 20% chance
                previous_macrosomia=random.choice([True, False, False, False]),  # 25% chance
                notes=f'Sample clinical data for patient {patient.first_name}'
            )
            
            db.session.add(metrics)
            db.session.flush()
            
            # Create a risk assessment
            # Generate a realistic risk score based on risk factors
            base_risk = 0.2
            if metrics.bmi and metrics.bmi > 30:
                base_risk += 0.2
            if metrics.family_history_diabetes:
                base_risk += 0.3
            if metrics.prediabetes_history:
                base_risk += 0.2
            if metrics.previous_gdm:
                base_risk += 0.4
            if patient.age > 35:
                base_risk += 0.1
            
            # Add some randomness
            risk_score = min(0.95, max(0.05, base_risk + random.uniform(-0.15, 0.15)))
            
            assessment = RiskAssessment(
                patient_id=patient.id,
                assessed_by=admin.id,
                input_vector=metrics.get_ml_input_vector(),
                risk_score=risk_score,
                model_version='1.0.0'
            )
            
            db.session.add(assessment)
            created_patients.append(patient)
        
        # Create audit log entries
        AuditLog.log_action(
            action=AuditAction.SYSTEM_STARTUP,
            details=f'Database seeded with {patients} sample patients'
        )
        
        # Commit all changes
        db.session.commit()
        
        click.echo(f'✅ Successfully created {len(created_patients)} patients with clinical data!')
        click.echo('\nSample patients created:')
        for patient in created_patients:
            latest_assessment = patient.latest_risk_assessment
            risk_info = f" (Risk: {latest_assessment.risk_label})" if latest_assessment else ""
            click.echo(f'  • {patient.full_name}, Age {patient.age}{risk_info}')
        
        click.echo(f'\nYou can now view patients at: http://localhost:5000/patients')
        
    except Exception as e:
        db.session.rollback()
        click.echo(f'Error creating sample data: {str(e)}')


@click.command()
@with_appcontext
def clear_data():
    """Clear all data from the database (except users)."""
    
    if not click.confirm('This will delete all patients, assessments, and reports. Continue?'):
        click.echo('Operation cancelled.')
        return
    
    try:
        # Delete in reverse order of dependencies
        AuditLog.query.filter(AuditLog.action != AuditAction.LOGIN_SUCCESS).delete()
        Report.query.delete()
        RiskAssessment.query.delete()
        ClinicalMetrics.query.delete()
        Patient.query.delete()
        
        db.session.commit()
        
        click.echo('✅ All data cleared successfully!')
        
    except Exception as e:
        db.session.rollback()
        click.echo(f'Error clearing data: {str(e)}')


def register_cli_commands(app):
    """Register CLI commands with the Flask app."""
    app.cli.add_command(create_admin)
    app.cli.add_command(init_db)
    app.cli.add_command(seed_data)
    app.cli.add_command(clear_data)