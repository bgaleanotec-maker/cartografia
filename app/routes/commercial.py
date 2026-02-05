from flask import Blueprint, render_template
from flask_login import login_required

commercial_bp = Blueprint('commercial', __name__, url_prefix='/commercial')

@commercial_bp.route('/new-visit')
@login_required
def new_visit():
    return render_template('commercial/new_visit.html')

@commercial_bp.route('/my-projects')
@login_required
def my_projects():
    # Show projects created by current user
    # Note: Using User.projects if relationship exists, else query
    from app.models.core import Project
    projects = Project.query.filter_by(commercial_user_id=current_user.id).all()
    return render_template('commercial/my_projects.html', projects=projects)
