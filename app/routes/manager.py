from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from app.models.core import Project
from app import db

manager_bp = Blueprint('manager', __name__, url_prefix='/manager')

@manager_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'manager' and current_user.role != 'admin':
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('main.index'))
        
    # Pending approvals
    pending_projects = Project.query.filter_by(status='pending_manager').all()
    return render_template('manager/dashboard.html', projects=pending_projects)

@manager_bp.route('/approve/<int:project_id>', methods=['POST'])
@login_required
def approve_project(project_id):
    project = Project.query.get_or_404(project_id)
    project.status = 'approved'
    project.manager_approval_status = 'approved'
    db.session.commit()
    flash(f'Proyecto {project.name} aprobado.', 'success')
    return redirect(url_for('manager.dashboard'))

@manager_bp.route('/reject/<int:project_id>', methods=['POST'])
@login_required
def reject_project(project_id):
    project = Project.query.get_or_404(project_id)
    comment = request.form.get('comment')
    project.status = 'rejected'
    project.manager_approval_status = 'rejected'
    project.manager_comment = comment
    db.session.commit()
    flash(f'Proyecto {project.name} rechazado.', 'warning')
    return redirect(url_for('manager.dashboard'))
