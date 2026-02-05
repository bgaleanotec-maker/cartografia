from flask import Blueprint, render_template
from flask_login import login_required, current_user

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@login_required
def index():
    if current_user.role == 'ejecutivo':
        return redirect(url_for('executive.dashboard'))
    return render_template('index.html', user=current_user)
@main_bp.route('/demo-roles')
def demo_roles():
    return render_template('demo_roles.html')
