import os
from flask import (Blueprint, render_template, request, Response, jsonify,
                   redirect, url_for, flash, current_app)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.models.core import Project, ProjectDocument
from app.models.user import User
from app.models.notification import Notification
from app.models.tracking import (ProcessRequest, PROCESS_TYPES, TERRAIN_OPTIONS,
                                  generate_tracking_id)
from app.services.email import email_service
from app import db
from sqlalchemy.orm import joinedload
from datetime import datetime

cartography_bp = Blueprint('cartography', __name__, url_prefix='/cartography')


def _get_or_create_process(project, ptype):
    proc = next((pr for pr in project.process_requests if pr.process_type == ptype), None)
    if not proc:
        ans = next((p['ans_days'] for p in PROCESS_TYPES if p['key'] == ptype), 15)
        proc = ProcessRequest(project_id=project.id, process_type=ptype, ans_days=ans,
                              estado='PENDIENTE')
        db.session.add(proc)
        db.session.flush()
    return proc

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
    
    # Asegurar las 3 solicitudes SGI
    for pt in PROCESS_TYPES:
        _get_or_create_process(project, pt['key'])
    db.session.commit()
    procs = {pr.process_type: pr for pr in project.process_requests}

    return render_template('cartography/project_detail.html',
                           project=project,
                           nodes_data=nodes_data,
                           documents_data=documents_data,
                           procs=procs,
                           terrain_options=TERRAIN_OPTIONS,
                           process_types=PROCESS_TYPES)

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

@cartography_bp.route('/project/<int:project_id>/export_kmz')
@login_required
def export_project_kmz(project_id):
    """Export project nodes as a KMZ file (Google Earth compatible)."""
    from app.services.kmz_service import generate_kmz
    project = Project.query.options(joinedload(Project.nodes)).filter_by(id=project_id).first_or_404()

    if not project.nodes:
        return Response("El proyecto no tiene nodos georreferenciados.", status=400, mimetype='text/plain')

    kmz_bytes = generate_kmz(project)
    safe_name = project.name.replace(' ', '_').replace('/', '-')[:40]
    filename = f"proyecto_{project.id}_{safe_name}.kmz"

    return Response(
        kmz_bytes,
        mimetype="application/vnd.google-earth.kmz",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Length": str(len(kmz_bytes))
        }
    )


@cartography_bp.route('/project/<int:project_id>/process/<ptype>/request', methods=['POST'])
@login_required
def request_process(project_id, ptype):
    """Inicia una solicitud SGI (Cartografía / Diseño / Informe Técnico).
    Registra # solicitud LF + fecha y arranca el ANS individual."""
    if ptype not in {p['key'] for p in PROCESS_TYPES}:
        return jsonify({'error': 'Tipo de proceso inválido'}), 400
    project = Project.query.get_or_404(project_id)
    proc = _get_or_create_process(project, ptype)

    proc.numero_solicitud = request.form.get('numero_solicitud') or proc.numero_solicitud
    if ptype == 'diseno':
        proc.numero_diseno = request.form.get('numero_diseno') or proc.numero_diseno
    if ptype == 'informe_tecnico':
        proc.requiere_visita = (request.form.get('requiere_visita') or '').upper() == 'SI'
    fecha = request.form.get('fecha_solicitud')
    from app.services import excel_service
    proc.fecha_solicitud = excel_service.parse_date(fecha) if fecha else datetime.utcnow()
    proc.estado = 'ABIERTO'  # arranca el ANS
    proc.recompute()

    # Etapa del proyecto segun el proceso
    stage_map = {'cartografia': '1. Cartografía', 'diseno': '2. Diseño',
                 'informe_tecnico': '3. Informe Técnico'}
    project.stage = stage_map.get(ptype, project.stage)

    # El Informe Tecnico genera formato y se envia por correo al area responsable
    if ptype == 'informe_tecnico':
        area_email = os.environ.get('PDI_AREA_EMAIL', 'proyectos@vanti.com')
        clients = sum((n.potential_clients_short or 0) + (n.potential_clients_long or 0)
                      for n in project.nodes) or project.potential_clients or 0
        meters = sum((n.manual_length or 0) for n in project.nodes)
        html = (f'<h3>Solicitud de Informe Técnico</h3>'
                f'<p><b>Proyecto:</b> {project.name} (ID {project.tracking_id or project.id})</p>'
                f'<p><b>Municipio:</b> {project.municipality or "—"} · <b>Malla:</b> {project.malla or "—"}</p>'
                f'<p><b>Dirección base:</b> {project.base_address or project.address or "—"}</p>'
                f'<p><b>Clientes potenciales:</b> {clients} · <b>Metros estimados:</b> {meters:.0f}</p>'
                f'<p><b>N° solicitud:</b> {proc.numero_solicitud or "—"}</p>')
        email_service.send(area_email, f'Solicitud Informe Técnico — {project.name}', html)

    db.session.commit()
    flash(f'Solicitud "{proc.label}" registrada. ANS iniciado ({proc.ans_days} días hábiles).', 'success')
    return redirect(url_for('cartography.project_detail', project_id=project_id) + '#gestion')


@cartography_bp.route('/project/<int:project_id>/process/<ptype>/response', methods=['POST'])
@login_required
def respond_process(project_id, ptype):
    """Registra la respuesta de una solicitud SGI (cierra ANS) y permite cargar
    el formato de respuesta (presupuesto del informe técnico)."""
    project = Project.query.get_or_404(project_id)
    proc = _get_or_create_process(project, ptype)

    fecha = request.form.get('fecha_respuesta')
    from app.services import excel_service
    proc.fecha_respuesta = excel_service.parse_date(fecha) if fecha else datetime.utcnow()
    proc.estado = 'CERRADO'

    # Cargar formato de respuesta (ej. presupuesto entregado)
    file = request.files.get('response_file')
    if file and file.filename:
        filename = secure_filename(file.filename)
        unique = f"{project_id}_{ptype}_RESP_{int(datetime.now().timestamp())}_{filename}"
        upload_dir = os.path.join(current_app.static_folder, 'uploads')
        os.makedirs(upload_dir, exist_ok=True)
        file.save(os.path.join(upload_dir, unique))
        proc.response_file = unique
        db.session.add(ProjectDocument(project_id=project_id, filename=unique,
                                       file_type=filename.rsplit('.', 1)[-1].lower()))

    proc.recompute()
    if proc.is_overdue:
        msg = f'La solicitud {proc.label} de {project.name} se cerró FUERA DE ANS.'
        for u in (project.cartographer, project.commercial):
            if u:
                db.session.add(Notification(user_id=u.id, title='⚠ ANS vencido',
                                            message=msg, notif_type='alert',
                                            link=url_for('cartography.project_detail', project_id=project_id)))
    db.session.commit()
    flash(f'Respuesta de "{proc.label}" registrada (tiempo de trámite: {proc.tiempo_tramite} días hábiles).', 'success')
    return redirect(url_for('cartography.project_detail', project_id=project_id) + '#gestion')


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
