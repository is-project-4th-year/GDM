from datetime import datetime, timedelta
from app import db


class AuditLog(db.Model):
    """Audit log model for tracking user actions and system events."""
    
    __tablename__ = 'audit_logs'
    
    # Primary key
    id = db.Column(db.Integer, primary_key=True)
    
    # User who performed the action
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Nullable for system events
    
    # Action details
    action = db.Column(db.String(50), nullable=False)  # LOGIN, CREATE_PATIENT, PREDICT, etc.
    entity = db.Column(db.String(50), nullable=True)  # patient, assessment, report, etc.
    entity_id = db.Column(db.Integer, nullable=True)  # ID of the affected entity
    
    # Additional context
    details = db.Column(db.Text, nullable=True)  # JSON string with additional details
    ip_address = db.Column(db.String(45), nullable=True)  # IPv4 or IPv6 address
    user_agent = db.Column(db.String(500), nullable=True)  # Browser/client information
    
    # System fields
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    user = db.relationship('User', backref='audit_logs')
    
    def __init__(self, action, user_id=None, entity=None, entity_id=None, 
                 details=None, ip_address=None, user_agent=None):
        """Initialize audit log entry."""
        self.action = action
        self.user_id = user_id
        self.entity = entity
        self.entity_id = entity_id
        self.details = details
        self.ip_address = ip_address
        self.user_agent = user_agent
    
    @property
    def user_name(self):
        """Get the name of the user who performed the action."""
        return self.user.name if self.user else "System"
    
    @property
    def user_email(self):
        """Get the email of the user who performed the action."""
        return self.user.email if self.user else "system@gdm.local"
    
    def to_dict(self):
        """Convert audit log to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': self.user_name,
            'user_email': self.user_email,
            'action': self.action,
            'entity': self.entity,
            'entity_id': self.entity_id,
            'details': self.details,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }
    
    @classmethod
    def log_action(cls, action, user_id=None, entity=None, entity_id=None, 
                   details=None, ip_address=None, user_agent=None):
        """Create and save an audit log entry."""
        log_entry = cls(
            action=action,
            user_id=user_id,
            entity=entity,
            entity_id=entity_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        db.session.add(log_entry)
        try:
            db.session.commit()
            return log_entry
        except Exception as e:
            db.session.rollback()
            # Log the error but don't fail the original operation
            print(f"Failed to create audit log: {str(e)}")
            return None
    
    @classmethod
    def log_login(cls, user_id, ip_address=None, user_agent=None, success=True):
        """Log user login attempt."""
        action = "LOGIN_SUCCESS" if success else "LOGIN_FAILED"
        return cls.log_action(
            action=action,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @classmethod
    def log_logout(cls, user_id, ip_address=None, user_agent=None):
        """Log user logout."""
        return cls.log_action(
            action="LOGOUT",
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @classmethod
    def log_patient_action(cls, action, patient_id, user_id, details=None):
        """Log patient-related actions."""
        return cls.log_action(
            action=action,
            user_id=user_id,
            entity="patient",
            entity_id=patient_id,
            details=details
        )
    
    @classmethod
    def log_assessment_action(cls, action, assessment_id, user_id, details=None):
        """Log risk assessment actions."""
        return cls.log_action(
            action=action,
            user_id=user_id,
            entity="assessment",
            entity_id=assessment_id,
            details=details
        )
    
    @classmethod
    def log_report_action(cls, action, report_id, user_id, details=None):
        """Log report generation actions."""
        return cls.log_action(
            action=action,
            user_id=user_id,
            entity="report",
            entity_id=report_id,
            details=details
        )
    
    @classmethod
    def get_recent_logs(cls, limit=100):
        """Get recent audit logs."""
        return cls.query.order_by(cls.timestamp.desc()).limit(limit).all()
    
    @classmethod
    def get_logs_for_user(cls, user_id, limit=50):
        """Get audit logs for a specific user."""
        return cls.query.filter_by(user_id=user_id).order_by(cls.timestamp.desc()).limit(limit).all()
    
    @classmethod
    def get_logs_by_action(cls, action, limit=50):
        """Get audit logs filtered by action type."""
        return cls.query.filter_by(action=action).order_by(cls.timestamp.desc()).limit(limit).all()
    
    @classmethod
    def get_logs_by_entity(cls, entity, entity_id=None, limit=50):
        """Get audit logs for a specific entity."""
        query = cls.query.filter_by(entity=entity)
        if entity_id:
            query = query.filter_by(entity_id=entity_id)
        return query.order_by(cls.timestamp.desc()).limit(limit).all()
    
    @classmethod
    def get_activity_summary(cls, days=30):
        """Get activity summary for the last N days."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        logs = cls.query.filter(cls.timestamp >= cutoff_date).all()
        
        summary = {
            'total_actions': len(logs),
            'unique_users': len(set(log.user_id for log in logs if log.user_id)),
            'actions_by_type': {},
            'actions_by_day': {},
            'entities_affected': {}
        }
        
        for log in logs:
            # Count by action type
            summary['actions_by_type'][log.action] = summary['actions_by_type'].get(log.action, 0) + 1
            
            # Count by day
            day_key = log.timestamp.date().isoformat()
            summary['actions_by_day'][day_key] = summary['actions_by_day'].get(day_key, 0) + 1
            
            # Count by entity
            if log.entity:
                summary['entities_affected'][log.entity] = summary['entities_affected'].get(log.entity, 0) + 1
        
        return summary
    
    @classmethod
    def cleanup_old_logs(cls, days_to_keep=365):
        """Clean up audit logs older than specified days."""
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        old_logs = cls.query.filter(cls.timestamp < cutoff_date)
        count = old_logs.count()
        
        old_logs.delete()
        db.session.commit()
        
        return count
    
    def __repr__(self):
        """String representation of audit log."""
        return f'<AuditLog {self.action} by User:{self.user_id} at {self.timestamp}>'


# Common audit actions (constants)
class AuditAction:
    """Constants for common audit actions."""
    
    # Authentication
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAILED = "LOGIN_FAILED"
    LOGOUT = "LOGOUT"
    
    # Patient management
    CREATE_PATIENT = "CREATE_PATIENT"
    UPDATE_PATIENT = "UPDATE_PATIENT"
    VIEW_PATIENT = "VIEW_PATIENT"
    DELETE_PATIENT = "DELETE_PATIENT"
    
    # Clinical metrics
    ADD_CLINICAL_METRICS = "ADD_CLINICAL_METRICS"
    UPDATE_CLINICAL_METRICS = "UPDATE_CLINICAL_METRICS"
    
    # Risk assessments
    PERFORM_ASSESSMENT = "PERFORM_ASSESSMENT"
    VIEW_ASSESSMENT = "VIEW_ASSESSMENT"
    
    # Reports
    GENERATE_REPORT = "GENERATE_REPORT"
    DOWNLOAD_REPORT = "DOWNLOAD_REPORT"
    
    # User management
    CREATE_USER = "CREATE_USER"
    UPDATE_USER = "UPDATE_USER"
    
    # System events
    SYSTEM_STARTUP = "SYSTEM_STARTUP"
    DATABASE_BACKUP = "DATABASE_BACKUP"