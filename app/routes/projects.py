from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from app.models.core import Project, FormTemplate
from app.services.email import email_service
from app import db
from datetime import datetime

projects_bp = Blueprint('projects', __name__, url_prefix='/projects')

@projects_bp.route('/dashboard')
@login_required
def dashboard():
    # Only show projects that have been approved (viable)
    projects = Project.query.filter_by(status='approved').all()
    return render_template('projects/dashboard.html', projects=projects)

@projects_bp.route('/approvals')
@login_required
def approvals():
    # Show projects pending approval
    projects = Project.query.filter(Project.viability_status != 'pending').all() 
    return render_template('projects/dashboard.html', projects=projects)

@projects_bp.route('/execution/<int:project_id>')
@login_required
def execution(project_id):
    project = Project.query.get_or_404(project_id)
    # Fetch criteria specific to current phase (e.g. hook='viability')
    templates = FormTemplate.query.filter_by(hook=project.phase).all()
    return render_template('projects/execution.html', project=project, templates=templates)

@projects_bp.route('/api/execution/<int:project_id>/update', methods=['POST'])
@login_required
def update_execution(project_id):
    project = Project.query.get_or_404(project_id)
    data = request.json
    
    old_status = project.execution_status
    
    # Handle Phase Transition
    if 'phase' in data:
        new_phase = data['phase']
        project.phase = new_phase
        now = datetime.utcnow()
        
        if new_phase == 'cartography': project.cartography_start_at = now
        elif new_phase == 'viability': project.viability_start_at = now
        elif new_phase == 'approval': project.approval_start_at = now
        elif new_phase == 'execution': project.execution_start_at = now
        elif new_phase == 'finished': project.finished_at = now
        
        db.session.commit()
        return jsonify({'status': 'success', 'new_phase': new_phase})
    
    # Handle existing Execution updates
    if 'progress' in data:
        project.execution_progress = int(data['progress'])
    
    if 'status' in data:
        project.execution_status = data['status']
        if project.execution_status != old_status:
             # Trigger notification
             email_service.send(
                 to_email='admin@vanti.com', # Hardcoded for demo/MVP
                 subject=f'Actualización de Proyecto: {project.name}',
                 html_content=f'<h1>Estado Actualizado</h1><p>El proyecto <b>{project.name}</b> ha cambiado su estado de ejecución a: {project.execution_status}</p>'
             )
        
    if 'start_date' in data and data['start_date']:
        try:
            project.start_date = datetime.strptime(data['start_date'], '%Y-%m-%d')
        except ValueError:
            pass 
            
    if 'end_date' in data and data['end_date']:
        try:
            project.end_date = datetime.strptime(data['end_date'], '%Y-%m-%d')
        except ValueError:
            pass

    db.session.commit()
    return jsonify({'status': 'success'})

@projects_bp.route('/control')
@login_required
def control_tower():
    # Only Admin or Project Engineer should see this in prod
    projects = Project.query.all()
    
    stats = {
        'total': len(projects),
        'in_viability': len([p for p in projects if p.phase == 'viability']),
        'in_execution': len([p for p in projects if p.phase == 'execution']),
        'finished': len([p for p in projects if p.phase == 'finished'])
    }
    
    return render_template('projects/dashboard_control.html', projects=projects, stats=stats)
