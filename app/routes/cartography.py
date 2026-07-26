import os
import json
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


def build_cotizacion_format(project):
    """Genera el FORMATO obligatorio de solicitud de cotización poblado con la
    información del proyecto: datos de la visita del EC + info del cartógrafo + proyecto."""
    ec = project.commercial.full_name if project.commercial else '—'
    ec_email = project.commercial.email if project.commercial else '—'
    cart = project.cartographer.full_name if project.cartographer else '—'
    # Consolidado de nodos (censo del cartógrafo)
    nodes = list(project.nodes)
    short = sum((n.potential_clients_short or n.potential_clients or 0) for n in nodes)
    long_ = sum((n.potential_clients_long or 0) for n in nodes)
    gas = sum((n.gas_points or 0) for n in nodes)
    meters = sum((n.manual_length or 0) for n in nodes)
    terrains = set()
    for n in nodes:
        try:
            for t in (json.loads(n.terrain_conditions) if n.terrain_conditions else []):
                terrains.add(t)
        except Exception:
            pass
    coord = (f"{project.latitude}, {project.longitude}"
             if project.latitude and project.longitude else '—')
    fecha = datetime.utcnow().strftime('%Y-%m-%d')

    rows = [
        ('ID de seguimiento', project.tracking_id or project.id),
        ('Proyecto', project.name or '—'),
        ('Municipio', project.municipality or '—'),
        ('Malla', project.malla or '—'),
        ('Dirección base', project.base_address or project.address or '—'),
        ('Coordenadas', coord),
        ('Ejecutivo Comercial', f'{ec} ({ec_email})'),
        ('Cartógrafo', cart),
        ('Clientes potenciales (corto plazo)', short),
        ('Clientes potenciales (largo plazo)', long_),
        ('Puntos de gas', gas),
        ('Metros de red estimados', f'{meters:.0f}'),
        ('Condiciones de terreno', ', '.join(sorted(terrains)) or '—'),
        ('Nodos levantados', len(nodes)),
        ('Fecha de solicitud', fecha),
    ]
    trs = ''.join(
        f'<tr><th style="text-align:left;background:#f1f5f9;padding:8px;border:1px solid #cbd5e1;'
        f'width:38%">{k}</th><td style="padding:8px;border:1px solid #cbd5e1">{v}</td></tr>'
        for k, v in rows)
    return f'''<div style="font-family:Arial,sans-serif;color:#0f172a;max-width:720px">
      <h2 style="margin-bottom:2px">Formato de Solicitud de Cotización — Informe Técnico</h2>
      <p style="color:#475569;margin-top:0">Vanti S.A. ESP · Gestión de Expansión de Redes</p>
      <table style="border-collapse:collapse;width:100%;font-size:13px">{trs}</table>
      <p style="font-size:12px;color:#64748b;margin-top:14px">Documento generado automáticamente por
      el Gestor Cartográfico. Se solicita al área responsable la cotización del proyecto de VT
      con base en la información anterior.</p>
    </div>'''

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

    from app.services import excel_service
    if ptype == 'informe_tecnico':
        # En Informe Tecnico NO se usa N° solicitud LF: se captura el destinatario del correo
        proc.recipient_email = request.form.get('recipient_email') or proc.recipient_email
        proc.requiere_visita = (request.form.get('requiere_visita') or '').upper() == 'SI'
    else:
        proc.numero_solicitud = request.form.get('numero_solicitud') or proc.numero_solicitud
        if ptype == 'diseno':
            proc.numero_diseno = request.form.get('numero_diseno') or proc.numero_diseno
    fecha = request.form.get('fecha_solicitud')
    proc.fecha_solicitud = excel_service.parse_date(fecha) if fecha else datetime.utcnow()
    proc.estado = 'ABIERTO'  # arranca el ANS
    proc.recompute()

    # Etapa del proyecto segun el proceso
    stage_map = {'cartografia': '1. Cartografía', 'diseno': '2. Diseño',
                 'informe_tecnico': '3. Informe Técnico'}
    project.stage = stage_map.get(ptype, project.stage)

    # El Informe Tecnico genera el FORMATO obligatorio poblado y lo envia por correo
    # al destinatario (IO que genera la cotizacion), con copia al Ejecutivo Comercial.
    if ptype == 'informe_tecnico':
        recipient = proc.recipient_email or os.environ.get('PDI_AREA_EMAIL', 'proyectos@vanti.com')
        formato = build_cotizacion_format(project)
        formato_url = url_for('cartography.formato_cotizacion', project_id=project.id, _external=True)
        body = (f'<p>Cordial saludo,</p>'
                f'<p>Se solicita la <b>cotización</b> del proyecto de VT <b>{project.name}</b> '
                f'(ID {project.tracking_id or project.id}). Adjunto el formato obligatorio con la '
                f'información del proyecto.</p>{formato}'
                f'<p><a href="{formato_url}">Ver / descargar el formato en la plataforma</a></p>')
        cc = [project.commercial.email] if (project.commercial and project.commercial.email) else None
        email_service.send(recipient, f'Solicitud de cotización — {project.name}', body, cc=cc)

    db.session.commit()
    dest = f' Correo enviado a {proc.recipient_email}.' if (ptype == 'informe_tecnico' and proc.recipient_email) else ''
    flash(f'Solicitud "{proc.label}" registrada. ANS iniciado ({proc.ans_days} días hábiles).{dest}', 'success')
    return redirect(url_for('cartography.project_detail', project_id=project_id) + '#gestion')


@cartography_bp.route('/project/<int:project_id>/formato-cotizacion')
@login_required
def formato_cotizacion(project_id):
    """Muestra el formato obligatorio de solicitud de cotización, poblado con
    la información del proyecto (visita EC + censo cartógrafo + proyecto)."""
    project = Project.query.get_or_404(project_id)
    html = build_cotizacion_format(project)
    page = (f'<!doctype html><html><head><meta charset="utf-8">'
            f'<title>Formato Cotización — {project.name}</title></head>'
            f'<body style="background:#f8fafc;padding:24px">'
            f'<div style="max-width:760px;margin:auto;background:#fff;padding:24px;'
            f'border-radius:8px;box-shadow:0 1px 4px rgba(0,0,0,.1)">{html}'
            f'<p style="margin-top:20px"><button onclick="window.print()" '
            f'style="background:#2563eb;color:#fff;border:0;padding:8px 16px;border-radius:6px;'
            f'cursor:pointer">Imprimir / Guardar PDF</button></p></div></body></html>')
    return Response(page, mimetype='text/html')


@cartography_bp.route('/project/<int:project_id>/send_to_executive', methods=['POST'])
@login_required
def send_to_executive(project_id):
    """Envía el proyecto al Ejecutivo Comercial para su proceso de aprobación."""
    project = Project.query.get_or_404(project_id)
    project.phase = 'approval'
    project.status = 'pending_review'
    project.stage = '4. Liberación presupuesto'
    project.approval_start_at = datetime.utcnow()
    db.session.commit()

    if project.commercial:
        db.session.add(Notification(
            user_id=project.commercial.id, title='Proyecto listo para aprobación',
            message=f'El cartógrafo envió {project.name} ({project.tracking_id or project.id}) '
                    f'para liberación de presupuesto / aprobación.',
            notif_type='task', link=url_for('executive.dashboard')))
        db.session.commit()
        if project.commercial.email:
            email_service.send(project.commercial.email,
                               f'Proyecto para aprobación — {project.name}',
                               f'<p>El proyecto <b>{project.name}</b> fue enviado por cartografía '
                               f'para su liberación de presupuesto y aprobación.</p>')
    flash('Proyecto enviado al Ejecutivo para aprobación.', 'success')
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
