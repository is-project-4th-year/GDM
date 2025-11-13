from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db


class User(UserMixin, db.Model):
    """User model for authentication and authorization."""
    
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='clinician')  # 'admin' or 'clinician'
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def __init__(self, name, email, password, role='clinician'):
        """Initialize user with hashed password."""
        self.name = name
        self.email = email.lower()  # Store emails in lowercase
        self.set_password(password)
        self.role = role
        self.is_active = True
    
    def set_password(self, password):
        """Hash and set password using PBKDF2."""
        self.password_hash = generate_password_hash(
            password,
            method='pbkdf2:sha256',
            salt_length=16
        )
    
    def check_password(self, password):
        """Check if provided password matches the hash."""
        return check_password_hash(self.password_hash, password)
    
    @property
    def is_admin(self):
        """Check if user has admin role."""
        return self.role == 'admin'
    
    @property
    def is_clinician(self):
        """Check if user has clinician role."""
        return self.role == 'clinician'
    
    def get_id(self):
        """Return user ID as string for Flask-Login."""
        return str(self.id)
    
    @property
    def is_authenticated(self):
        """Flask-Login property: True if user is authenticated."""
        return True
    
    @property
    def is_anonymous(self):
        """Flask-Login property: False for regular users."""
        return False
    
    def __repr__(self):
        """String representation of user."""
        return f'<User {self.email} ({self.role})>'
    
    @classmethod
    def create_admin(cls, name, email, password):
        """Create admin user."""
        return cls(name=name, email=email, password=password, role='admin')
    
    @classmethod
    def create_clinician(cls, name, email, password):
        """Create clinician user."""
        return cls(name=name, email=email, password=password, role='clinician')