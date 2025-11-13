from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user

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
    """Main dashboard (requires authentication)."""
    return render_template('dashboard.html', user=current_user)