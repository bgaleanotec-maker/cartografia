from flask import Blueprint, render_template, request
from flask_login import login_required
from app.models.core import Project
from app import db
from sqlalchemy.orm import joinedload
from datetime import datetime

cartography_bp = Blueprint('cartography', __name__, url_prefix='/cartography')

@cartography_bp.route('/inbox')
@login_required
def inbox():
    projects = Project.query.order_by(Project.created_at.desc()).all()
    return render_template('cartography/inbox.html', projects=projects)

@cartography_bp.route('/project/<int:project_id>')
@login_required
def project_detail(project_id):
    # Eager load documents to ensure they are available for the template
    project = Project.query.options(joinedload(Project.documents)).filter_by(id=project_id).first_or_404()
    
    # Serialize nodes for safe JS injection
    nodes_data = []
    for node in project.nodes:
        n = node.to_dict()
        # Add frontend-specific aliases
        n['lat'] = node.latitude
        n['lng'] = node.longitude
        # Ensure 'cond' maps to something useful if needed, or rely on frontend default
        if node.has_water_source:
            n['cond'] = 'water'
        elif node.is_rocky_ground:
            n['cond'] = 'rocky'
        else:
            n['cond'] = 'normal'
            
        n['seq'] = node.sequence
        n['clients'] = node.potential_clients
        n['gas'] = node.gas_points
        n['obs'] = node.observations
        nodes_data.append(n)

    # Serialize documents for safe JS injection
    from flask import url_for
    documents_data = []
    for doc in project.documents:
        d = doc.to_dict()
        # Add frontend-specific fields
        d['name'] = doc.filename
        d['url'] = url_for('static', filename='uploads/' + doc.filename)
        d['raw_name'] = doc.filename
        d['date'] = doc.uploaded_at.strftime('%Y-%m-%d')
        documents_data.append(d)
    
    return render_template('cartography/project_detail.html', 
                           project=project, 
                           nodes_data=nodes_data, 
                           documents_data=documents_data)

@cartography_bp.route('/api/export/<int:project_id>')
@login_required
def export_project_csv(project_id):
    project = Project.query.get_or_404(project_id)
    
    import csv
    import io
    from flask import Response
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(['Sequence', 'Latitude', 'Longitude', 'Manual Length', 'Pot. Clients', 'Gas Points'])
    
    # Data
    for node in project.nodes:
        writer.writerow([
            node.sequence, 
            node.latitude, 
            node.longitude, 
            node.manual_length,
            node.potential_clients,
            node.gas_points
        ])
        
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename=project_{project.id}_nodes.csv"}
    )

@cartography_bp.route('/api/export_all')
@login_required
def export_all_csv():
    # Helper for filtering
    from sqlalchemy import or_
    import csv
    import io
    from flask import Response
    from datetime import datetime
    
    name_filter = request.args.get('name', '')
    date_filter = request.args.get('date', '')
    
    query = Project.query
    if name_filter:
        query = query.filter(Project.name.ilike(f'%{name_filter}%'))
    if date_filter:
        try:
            date_obj = datetime.strptime(date_filter, '%Y-%m-%d')
            # Filter by creating day
            query = query.filter(db.func.date(Project.created_at) == date_obj.date())
        except ValueError:
            pass
            
    projects = query.all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(['Project ID', 'Project Name', 'Creation Date', 'Address', 'Total Nodes', 'Status', 'Phase'])
    
    for p in projects:
        writer.writerow([
            p.id,
            p.name,
            p.created_at.strftime('%Y-%m-%d'),
            p.address,
            len(p.nodes),
            p.status,
            p.phase
        ])
        
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=all_projects_report.csv"}
    )

@cartography_bp.route('/project/<int:project_id>/send_to_viability', methods=['POST'])
@login_required
def send_to_viability(project_id):
    project = Project.query.get_or_404(project_id)
    
    # Logic: Cartographer finishes work, sends to Projects
    project.phase = 'viability'
    project.status = 'pending_review'
    # project.cartography_end_at = datetime.utcnow() # If we had this field
    project.viability_start_at = datetime.utcnow()
    
    db.session.commit()
    return {'status': 'success', 'message': 'Proyecto enviado a viabilidad (Proyectos)'}

@cartography_bp.route('/project/<int:project_id>/submit_viability', methods=['POST'])
@login_required
def submit_viability(project_id):
    project = Project.query.get_or_404(project_id)
    
    # Logic: Projects finishes checklist, sends to Manager
    project.phase = 'approval' # or 'manager_review'
    project.status = 'pending_approval'
    project.viability_status = 'viable' # Assuming positive flow for now
    project.approval_start_at = datetime.utcnow()
    
    # In a real scenario, we would validate that the form/checklist is complete here
    
    db.session.commit()
    return {'status': 'success', 'message': 'Proyecto enviado a Gerencia para aprobación'}

@cartography_bp.route('/project/<int:project_id>/approve', methods=['POST'])
@login_required
def approve_project(project_id):
    project = Project.query.get_or_404(project_id)
    
    # Logic: Manager approves
    project.phase = 'execution'
    project.status = 'approved'
    project.manager_approval_status = 'approved'
    project.execution_start_at = datetime.utcnow()
    
    db.session.commit()
    return {'status': 'success', 'message': 'Proyecto aprobado e iniciado para ejecución'}
