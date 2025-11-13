from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from urllib.parse import urlparse

from app import db
from app.models.user import User

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


class LoginForm(FlaskForm):
    """Login form with email and password."""
    
    email = StringField('Email Address', validators=[
        DataRequired(message='Email is required'),
        Email(message='Please enter a valid email address')
    ], render_kw={'placeholder': 'Enter your email', 'class': 'form-control'})
    
    password = PasswordField('Password', validators=[
        DataRequired(message='Password is required')
    ], render_kw={'placeholder': 'Enter your password', 'class': 'form-control'})
    
    submit = SubmitField('Log In', render_kw={'class': 'btn btn-primary w-100'})


class RegisterForm(FlaskForm):
    """Registration form (admin only)."""
    
    name = StringField('Full Name', validators=[
        DataRequired(message='Full name is required'),
        Length(min=2, max=100, message='Name must be between 2 and 100 characters')
    ], render_kw={'placeholder': 'Enter full name', 'class': 'form-control'})
    
    email = StringField('Email Address', validators=[
        DataRequired(message='Email is required'),
        Email(message='Please enter a valid email address'),
        Length(max=120, message='Email must be less than 120 characters')
    ], render_kw={'placeholder': 'Enter email address', 'class': 'form-control'})
    
    password = PasswordField('Password', validators=[
        DataRequired(message='Password is required'),
        Length(min=8, message='Password must be at least 8 characters long')
    ], render_kw={'placeholder': 'Enter password', 'class': 'form-control'})
    
    password_confirm = PasswordField('Confirm Password', validators=[
        DataRequired(message='Please confirm your password'),
        EqualTo('password', message='Passwords must match')
    ], render_kw={'placeholder': 'Confirm password', 'class': 'form-control'})
    
    role = SelectField('Role', choices=[
        ('clinician', 'Clinician'),
        ('admin', 'Administrator')
    ], default='clinician', validators=[
        DataRequired()
    ], render_kw={'class': 'form-select'})
    
    submit = SubmitField('Create User', render_kw={'class': 'btn btn-success w-100'})
    
    def validate_email(self, field):
        """Check if email already exists."""
        user = User.query.filter_by(email=field.data.lower()).first()
        if user:
            raise ValidationError('Email address already registered.')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login."""
    
    # Redirect if already logged in
    if current_user.is_authenticated:
        return redirect(url_for('core.dashboard'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        password = form.password.data
        
        # Find user by email
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            if user.is_active:
                # Log in the user
                login_user(user, remember=True)
                
                # Flash success message
                flash(f'Welcome back, {user.name}!', 'success')
                
                # Redirect to next page or dashboard
                next_page = request.args.get('next')
                if not next_page or url_parse(next_page).netloc != '':
                    next_page = url_for('core.dashboard')
                
                return redirect(next_page)
            else:
                flash('Your account has been deactivated. Please contact an administrator.', 'error')
        else:
            flash('Invalid email or password. Please try again.', 'error')
    
    return render_template('login.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    """Handle user logout."""
    name = current_user.name
    logout_user()
    flash(f'You have been logged out successfully. Goodbye, {name}!', 'info')
    return redirect(url_for('core.index'))


@auth_bp.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    """Handle user registration (admin only)."""
    
    # Check if current user is admin
    if not current_user.is_admin:
        flash('Access denied. Only administrators can register new users.', 'error')
        return redirect(url_for('core.dashboard'))
    
    form = RegisterForm()
    
    if form.validate_on_submit():
        try:
            # Create new user
            user = User(
                name=form.name.data.strip(),
                email=form.email.data.lower().strip(),
                password=form.password.data,
                role=form.role.data
            )
            
            # Save to database
            db.session.add(user)
            db.session.commit()
            
            flash(f'User {user.name} ({user.email}) created successfully with role: {user.role.title()}', 'success')
            
            # Clear form for next user
            return redirect(url_for('auth.register'))
            
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while creating the user. Please try again.', 'error')
    
    return render_template('register.html', form=form)


# Import ValidationError after form definitions
from wtforms.validators import ValidationError
