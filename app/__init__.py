import os
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

from app.config import config

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')
    
    # Get the absolute path to the project root
    basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    
    # Create Flask app with explicit paths
    app = Flask(__name__, 
                template_folder=os.path.join(basedir, 'templates'),
                static_folder=os.path.join(basedir, 'static'))
    
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    
    # Configure Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        """Load user by ID for Flask-Login."""
        from app.models.user import User
        return User.query.get(int(user_id))
    
    # Register blueprints
    from app.routes.core import core_bp
    from app.routes.auth import auth_bp
    
    app.register_blueprint(core_bp)
    app.register_blueprint(auth_bp)
    
    # Register CLI commands
    from cli_commands import register_cli_commands
    register_cli_commands(app)
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return render_template('error.html', 
                             error_code=404, 
                             error_message="Page not found"), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('error.html', 
                             error_code=500, 
                             error_message="Internal server error"), 500
    
    return app
