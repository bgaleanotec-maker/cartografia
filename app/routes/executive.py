from flask import Blueprint, render_template
from flask_login import login_required

executive_bp = Blueprint('executive', __name__, url_prefix='/executive')

@executive_bp.route('/dashboard')
@login_required
def dashboard():
    return render_template('executive/dashboard.html')
