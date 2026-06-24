"""
tracking.py — Tabla maestra "Gestion - Apoyo Cartografia" (SGI)
================================================================
Grid editable en vivo + carga con plantilla + config de campos por ejecutivo +
gestion de equipos (ejecutivo<->cartografo) con reasignacion/vacaciones.
"""
import io
import os
import secrets
from datetime import datetime

from flask import (Blueprint, render_template, request, jsonify, redirect,
                   url_for, flash, Response, current_app)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app import db
from app.models.core import Project
from app.models.user import User
from app.models.notification import Notification
from app.models.tracking import (ProcessRequest, TeamAssignment, ExecutiveFieldConfig,
                                  FIELD_CATALOG, STAGE_OPTIONS, ESTADO_OPTIONS,
                                  PROCESS_TYPES, get_field_config, generate_tracking_id)
from app.services import excel_service
from app.services.email import email_service

tracking_bp = Blueprint('tracking', __name__, url_prefix='/seguimiento')


# ── Helpers ─────────────────────────────────────────────────────────────────

def _can_manage():
    return current_user.is_superadmin or current_user.role in (
        'admin', 'cartography', 'commercial', 'executive', 'manager')


def _norm(s):
    return (s or '').strip().lower()


def _resolve_commercial(name):
    """Encuentra (o crea) un ejecutivo comercial por nombre, normalizando mayusculas."""
    if not name:
        return None
    target = _norm(name)
    for u in User.query.filter(User.role.in_(('commercial', 'executive'))).all():
        if _norm(u.full_name) == target or _norm(u.username) == target:
            return u
    # Crear ejecutivo nuevo si no existe
    clean = ' '.join(w.capitalize() for w in name.strip().split())
    username = _norm(clean).replace(' ', '.')
    user = User(username=username[:60], full_name=clean, role='commercial',
                is_active=True, api_key=secrets.token_hex(24))
    user.set_password(secrets.token_hex(8))
    db.session.add(user)
    db.session.flush()
    return user


def _ensure_processes(project):
    """Garantiza que existan las 3 solicitudes SGI del proyecto."""
    existing = {pr.process_type for pr in project.process_requests}
    for pt in PROCESS_TYPES:
        if pt['key'] not in existing:
            db.session.add(ProcessRequest(project_id=project.id, process_type=pt['key'],
                                          ans_days=pt['ans_days'], estado='PENDIENTE'))


def _notify_overdue(project, proc):
    """Crea notificacion + correo al detectar fuera de ANS."""
    msg = (f'La solicitud {proc.label} del proyecto {project.name} '
           f'({project.tracking_id or project.id}) está FUERA DE ANS.')
    targets = [u for u in (project.cartographer, project.commercial) if u]
    for u in targets:
        db.session.add(Notification(
            user_id=u.id, title='⚠ ANS vencido', message=msg, notif_type='alert',
            link=url_for('tracking.index')))
        if u.email:
            email_service.send(u.email, 'Alerta ANS vencido', f'<p>{msg}</p>')


# ── Grid maestro ──────────────────────────────────────────────────────────────

@tracking_bp.route('/')
@login_required
def index():
    if not _can_manage():
        flash('Acceso no autorizado.', 'error')
        return redirect(url_for('main.index'))

    f_exec = request.args.get('executive', type=int)
    f_cart = request.args.get('cartographer', type=int)
    f_muni = request.args.get('municipality', '')
    f_stage = request.args.get('stage', '')

    query = Project.query
    # El cartografo solo ve su cola por defecto (salvo que pida ver todo)
    if current_user.role == 'cartography' and not request.args.get('all'):
        query = query.filter(Project.cartographer_user_id == current_user.id)
    if f_exec:
        query = query.filter(Project.commercial_user_id == f_exec)
    if f_cart:
        query = query.filter(Project.cartographer_user_id == f_cart)
    if f_muni:
        query = query.filter(Project.municipality == f_muni)
    if f_stage:
        query = query.filter(Project.stage == f_stage)

    projects = query.order_by(Project.created_at.desc()).all()

    # Asegurar procesos y mapearlos
    changed = False
    for p in projects:
        before = p.process_requests.count()
        _ensure_processes(p)
        if p.process_requests.count() != before:
            changed = True
    if changed:
        db.session.commit()

    rows = []
    for p in projects:
        procs = {pr.process_type: pr for pr in p.process_requests}
        rows.append({'project': p, 'cartografia': procs.get('cartografia'),
                     'diseno': procs.get('diseno'), 'informe_tecnico': procs.get('informe_tecnico')})

    executives = User.query.filter(User.role.in_(('commercial', 'executive'))).all()
    cartographers = User.query.filter_by(role='cartography').all()
    municipalities = [m[0] for m in db.session.query(Project.municipality)
                      .filter(Project.municipality.isnot(None)).distinct().all()]

    # Config de campos: usa la del ejecutivo filtrado, o el catalogo base
    field_config = get_field_config(f_exec) if f_exec else get_field_config(None)
    visible_keys = {f['key'] for f in field_config if f['visible']}

    return render_template('tracking/index.html', rows=rows, executives=executives,
                           cartographers=cartographers, municipalities=municipalities,
                           stage_options=STAGE_OPTIONS, estado_options=ESTADO_OPTIONS,
                           visible_keys=visible_keys,
                           f_exec=f_exec, f_cart=f_cart, f_muni=f_muni, f_stage=f_stage)


@tracking_bp.route('/proyecto/nuevo', methods=['POST'])
@login_required
def new_project():
    """Crea un proyecto rapido desde el grid."""
    data = request.json if request.is_json else request.form
    name = data.get('name')
    if not name:
        return jsonify({'error': 'Nombre requerido'}), 400
    p = Project(name=name, municipality=data.get('municipality'),
                relevancia=data.get('relevancia'), stage='0. Definición alcance',
                tracking_id=generate_tracking_id())
    if data.get('executive'):
        p.commercial_user_id = int(data['executive'])
    db.session.add(p)
    db.session.flush()
    _ensure_processes(p)
    db.session.commit()
    return jsonify({'status': 'success', 'id': p.id})


@tracking_bp.route('/proyecto/<int:project_id>/inline', methods=['POST'])
@login_required
def update_project_inline(project_id):
    """Actualiza una celda del proyecto (estado/etapa/fechas/notas/asignacion)."""
    p = Project.query.get_or_404(project_id)
    data = request.json or {}
    field = data.get('field')
    value = data.get('value')

    date_fields = {'assigned_date', 'visit_date'}
    text_fields = {'municipality', 'relevancia', 'name', 'base_address', 'malla',
                   'stage', 'support_notes', 'pdi_notes'}
    if field in date_fields:
        setattr(p, field, excel_service.parse_date(value))
    elif field == 'potential_clients':
        p.potential_clients = int(value or 0)
    elif field == 'commercial_user_id':
        p.commercial_user_id = int(value) if value else None
    elif field == 'cartographer_user_id':
        p.cartographer_user_id = int(value) if value else None
    elif field in text_fields:
        setattr(p, field, value)
    else:
        return jsonify({'error': f'Campo no permitido: {field}'}), 400

    db.session.commit()
    return jsonify({'status': 'success'})


@tracking_bp.route('/proceso/<int:proc_id>/inline', methods=['POST'])
@login_required
def update_process_inline(proc_id):
    """Actualiza una celda de una solicitud SGI y recalcula ANS/tiempo de tramite."""
    proc = ProcessRequest.query.get_or_404(proc_id)
    data = request.json or {}
    field = data.get('field')
    value = data.get('value')

    if field in ('numero_solicitud', 'numero_diseno', 'observaciones'):
        setattr(proc, field, value)
    elif field in ('fecha_solicitud', 'fecha_respuesta', 'fecha_visita_cotizacion'):
        setattr(proc, field, excel_service.parse_date(value))
    elif field == 'estado':
        proc.estado = value
    elif field == 'requiere_visita':
        proc.requiere_visita = str(value).upper() in ('SI', 'TRUE', '1')
    else:
        return jsonify({'error': f'Campo no permitido: {field}'}), 400

    proc.recompute()
    # Alerta si quedo fuera de ANS
    if proc.is_overdue:
        _notify_overdue(proc.project, proc)
    db.session.commit()
    return jsonify({'status': 'success', 'process': proc.to_dict()})


@tracking_bp.route('/proyecto/<int:project_id>/asignar', methods=['POST'])
@login_required
def assign_cartographer(project_id):
    p = Project.query.get_or_404(project_id)
    cart_id = request.form.get('cartographer_id', type=int)
    p.cartographer_user_id = cart_id or None
    db.session.commit()
    if cart_id:
        cart = User.query.get(cart_id)
        db.session.add(Notification(
            user_id=cart_id, title='Nuevo proyecto asignado',
            message=f'Se te asignó el proyecto {p.name} ({p.tracking_id or p.id}).',
            notif_type='task', link=url_for('tracking.index')))
        db.session.commit()
        if cart and cart.email:
            email_service.send(cart.email, 'Proyecto asignado',
                               f'<p>Se te asignó el proyecto <b>{p.name}</b>.</p>')
    flash('Cartógrafo asignado.', 'success')
    return redirect(request.referrer or url_for('tracking.index'))


# ── Plantilla / Importar / Exportar ────────────────────────────────────────────

@tracking_bp.route('/plantilla')
@login_required
def download_template():
    data = excel_service.build_template()
    return Response(data, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    headers={'Content-Disposition': 'attachment; filename=plantilla_seguimiento_cartografia.xlsx'})


@tracking_bp.route('/importar', methods=['POST'])
@login_required
def import_excel():
    file = request.files.get('file')
    if not file or not file.filename.endswith(('.xlsx', '.xlsm')):
        flash('Sube un archivo .xlsx válido.', 'error')
        return redirect(url_for('tracking.index'))

    try:
        records = excel_service.parse_import(file.stream)
    except Exception as e:
        flash(f'Error leyendo el archivo: {e}', 'error')
        return redirect(url_for('tracking.index'))

    created, updated = 0, 0
    for rec in records:
        muni = rec.get('municipality')
        name = rec.get('name')
        # Upsert por (municipio + proyecto) normalizado
        existing = next((p for p in Project.query.filter_by(name=name).all()
                         if _norm(p.municipality) == _norm(muni)), None)
        p = existing or Project(name=name)
        if not existing:
            p.tracking_id = generate_tracking_id()
            db.session.add(p)

        p.municipality = muni
        p.relevancia = rec.get('relevancia')
        p.stage = rec.get('stage') or p.stage
        p.potential_clients = int(rec.get('potential_clients') or 0)
        p.assigned_date = excel_service.parse_date(rec.get('assigned_date'))
        p.visit_date = excel_service.parse_date(rec.get('visit_date'))
        p.support_notes = rec.get('support_notes')
        p.pdi_notes = rec.get('pdi_notes')
        comm = _resolve_commercial(rec.get('commercial'))
        if comm:
            p.commercial_user_id = comm.id
        db.session.flush()

        _ensure_processes(p)
        db.session.flush()
        procs = {pr.process_type: pr for pr in p.process_requests}
        _apply_process(procs.get('cartografia'), rec, 'cartografia')
        _apply_process(procs.get('diseno'), rec, 'diseno')
        _apply_process(procs.get('informe_tecnico'), rec, 'informe_tecnico')

        if existing:
            updated += 1
        else:
            created += 1

    db.session.commit()
    flash(f'Importación completada: {created} creados, {updated} actualizados.', 'success')
    return redirect(url_for('tracking.index'))


def _apply_process(proc, rec, prefix):
    if not proc:
        return
    proc.numero_solicitud = rec.get(f'{prefix}.numero_solicitud') or proc.numero_solicitud
    if prefix == 'diseno':
        proc.numero_diseno = rec.get('diseno.numero_diseno') or proc.numero_diseno
    proc.fecha_solicitud = excel_service.parse_date(rec.get(f'{prefix}.fecha_solicitud')) or proc.fecha_solicitud
    proc.fecha_respuesta = excel_service.parse_date(rec.get(f'{prefix}.fecha_respuesta')) or proc.fecha_respuesta
    estado = rec.get(f'{prefix}.estado')
    if estado:
        proc.estado = str(estado).upper()
    if prefix == 'informe_tecnico':
        proc.requiere_visita = _norm(rec.get('informe_tecnico.requiere_visita')) in ('si', 'sí', 'true', '1')
        proc.fecha_visita_cotizacion = excel_service.parse_date(rec.get('informe_tecnico.fecha_visita_cotizacion')) or proc.fecha_visita_cotizacion
    proc.recompute()


@tracking_bp.route('/exportar')
@login_required
def export_excel():
    projects = Project.query.order_by(Project.created_at.desc()).all()
    data = excel_service.build_export(projects)
    ts = datetime.utcnow().strftime('%Y%m%d')
    return Response(data, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    headers={'Content-Disposition': f'attachment; filename=seguimiento_cartografia_{ts}.xlsx'})


# ── Configuracion de campos por ejecutivo ──────────────────────────────────────

@tracking_bp.route('/campos', methods=['GET', 'POST'])
@login_required
def field_config():
    if not (current_user.is_superadmin or current_user.role in ('admin', 'manager')):
        flash('Acceso no autorizado.', 'error')
        return redirect(url_for('tracking.index'))

    executives = User.query.filter(User.role.in_(('commercial', 'executive'))).all()
    exec_id = request.values.get('executive', type=int) or (executives[0].id if executives else None)

    if request.method == 'POST' and exec_id:
        # Borrar config previa y reescribir
        ExecutiveFieldConfig.query.filter_by(commercial_user_id=exec_id).delete()
        for idx, field in enumerate(FIELD_CATALOG):
            db.session.add(ExecutiveFieldConfig(
                commercial_user_id=exec_id, field_key=field['key'],
                visible=request.form.get(f"visible_{field['key']}") == 'on',
                required=request.form.get(f"required_{field['key']}") == 'on',
                sequence=idx))
        db.session.commit()
        flash('Configuración de campos guardada.', 'success')
        return redirect(url_for('tracking.field_config', executive=exec_id))

    config = get_field_config(exec_id)
    return render_template('tracking/field_config.html', executives=executives,
                           exec_id=exec_id, config=config)


# ── Equipos (ejecutivo <-> cartografo) ──────────────────────────────────────────

@tracking_bp.route('/equipos', methods=['GET', 'POST'])
@login_required
def teams():
    if not (current_user.is_superadmin or current_user.role in ('admin', 'manager', 'executive', 'commercial')):
        flash('Acceso no autorizado.', 'error')
        return redirect(url_for('tracking.index'))

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'assign':
            exec_id = request.form.get('executive_id', type=int)
            cart_id = request.form.get('cartographer_id', type=int)
            note = request.form.get('note', '')
            if exec_id and cart_id:
                ta = TeamAssignment.query.filter_by(executive_id=exec_id, cartographer_id=cart_id).first()
                if ta:
                    ta.active = True
                    ta.end_date = None
                    ta.note = note
                else:
                    db.session.add(TeamAssignment(executive_id=exec_id, cartographer_id=cart_id, note=note))
                db.session.commit()
                flash('Cartógrafo asignado al ejecutivo.', 'success')
        elif action == 'toggle':
            ta = TeamAssignment.query.get(request.form.get('assignment_id', type=int))
            if ta:
                ta.active = not ta.active
                ta.end_date = datetime.utcnow() if not ta.active else None
                ta.note = request.form.get('note', ta.note)
                db.session.commit()
                flash('Estado de asignación actualizado (vacaciones/reasignación).', 'success')
        return redirect(url_for('tracking.teams'))

    executives = User.query.filter(User.role.in_(('commercial', 'executive'))).all()
    cartographers = User.query.filter_by(role='cartography').all()
    assignments = TeamAssignment.query.all()
    return render_template('tracking/teams.html', executives=executives,
                           cartographers=cartographers, assignments=assignments)


@tracking_bp.route('/check-ans')
@login_required
def check_ans():
    """Escanea solicitudes abiertas y notifica las vencidas (alarma manual/cron)."""
    overdue = 0
    for proc in ProcessRequest.query.filter_by(estado='ABIERTO').all():
        if proc.is_overdue:
            _notify_overdue(proc.project, proc)
            overdue += 1
    db.session.commit()
    return jsonify({'status': 'success', 'overdue': overdue})
