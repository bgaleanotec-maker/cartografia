from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from app.models.core import Project
from app import db

analyst_bp = Blueprint('analyst', __name__, url_prefix='/analyst')

@analyst_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'analyst' and current_user.role != 'admin':
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('main.index'))
        
    projects = Project.query.filter_by(commercial_user_id=current_user.id).all()
    return render_template('analyst/dashboard.html', projects=projects)

@analyst_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_project():
    if request.method == 'POST':
        name = request.form.get('name')
        p_type = request.form.get('project_type')
        desc = request.form.get('description')
        
        project = Project(
            name=name,
            project_type=p_type,
            description=desc,
            status='prospecting', # Starts here
            commercial_user_id=current_user.id
        )
        db.session.add(project)
        db.session.commit()
        
        flash('Proyecto creado exitosamente', 'success')
        return redirect(url_for('analyst.dashboard'))
        
    return render_template('analyst/create.html')
