"""
executive.py — Rol Ejecutivo Comercial
=======================================
- Nueva Visita: inicia el flujo del proyecto (genera ID de seguimiento y lo
  envia a un cartografo).
- Liberacion de presupuesto: valor total / valor por cliente y liberar a Gerencia.
"""
from datetime import datetime

from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, jsonify)
from flask_login import login_required, current_user

from app import db
from app.models.core import Project
from app.models.user import User
from app.models.notification import Notification
from app.models.tracking import generate_tracking_id, PROCESS_TYPES, ProcessRequest
from app.services.email import email_service

executive_bp = Blueprint('executive', __name__, url_prefix='/executive')


def _ensure_processes(project):
    existing = {pr.process_type for pr in project.process_requests}
    for pt in PROCESS_TYPES:
        if pt['key'] not in existing:
            db.session.add(ProcessRequest(project_id=project.id, process_type=pt['key'],
                                          ans_days=pt['ans_days'], estado='PENDIENTE'))


@executive_bp.route('/dashboard')
@login_required
def dashboard():
    # Proyectos del ejecutivo (o todos si admin/superadmin)
    if current_user.is_superadmin or current_user.role == 'admin':
        my_projects = Project.query.order_by(Project.created_at.desc()).all()
    else:
        my_projects = Project.query.filter_by(commercial_user_id=current_user.id)\
            .order_by(Project.created_at.desc()).all()

    cartographers = User.query.filter_by(role='cartography').all()
    # Proyectos listos para liberar presupuesto (con informe tecnico cerrado o en etapa avanzada)
    budget_projects = [p for p in my_projects
                       if (p.stage or '').startswith(('3.', '4.')) or p.total_value]
    pending_budget = [p for p in budget_projects if p.manager_status == 'pending_approval'
                      and (p.total_value or 0) == 0]
    # Proyectos aprobados por Gerencia -> gestion de mascara / SAP
    mask_projects = [p for p in my_projects if p.manager_status == 'approved']
    return render_template('executive/dashboard.html', projects=my_projects,
                           cartographers=cartographers, budget_projects=budget_projects,
                           mask_projects=mask_projects,
                           pending_budget_count=len(pending_budget))


@executive_bp.route('/mask/<int:project_id>', methods=['POST'])
@login_required
def update_mask(project_id):
    """EC ingresa el número de máscara y la fecha de carga en SAP (arranca contador)."""
    p = Project.query.get_or_404(project_id)
    mask = request.form.get('mask_number', '').strip()
    sap_date = request.form.get('sap_budget_date', '').strip()
    from app.services import excel_service

    if mask and mask != (p.mask_number or ''):
        p.mask_number = mask
        if not p.mask_received_at:
            p.mask_received_at = datetime.utcnow()
    if sap_date:
        p.sap_budget_date = excel_service.parse_date(sap_date)
        p.stage = '6. Ejecución'
    db.session.commit()
    flash('Datos de máscara / SAP actualizados.', 'success')
    return redirect(url_for('executive.dashboard'))


@executive_bp.route('/new-visit', methods=['POST'])
@login_required
def new_visit():
    """Crea proyecto, genera ID de seguimiento y lo envia a un cartografo."""
    f = request.form
    name = f.get('name')
    if not name:
        flash('El nombre del proyecto es obligatorio.', 'error')
        return redirect(url_for('executive.dashboard'))

    def _flt(v):
        try:
            return float(v) if v not in (None, '') else None
        except ValueError:
            return None

    p = Project(
        name=name,
        tracking_id=generate_tracking_id(),
        base_address=f.get('base_address'),
        municipality=f.get('municipality'),
        malla=f.get('malla'),
        relevancia=f.get('relevancia') or 'MESA DE TRABAJO',
        latitude=_flt(f.get('latitude')),
        longitude=_flt(f.get('longitude')),
        potential_clients=int(f.get('potential_clients') or 0),
        commercial_user_id=current_user.id if current_user.role in ('commercial', 'executive') else (f.get('executive_id', type=int)),
        cartographer_user_id=f.get('cartographer_id', type=int),
        stage='0. Definición alcance',
        phase='cartography',
        status='prospecting',
        assigned_date=datetime.utcnow(),
        cartography_start_at=datetime.utcnow(),
    )
    db.session.add(p)
    db.session.flush()
    _ensure_processes(p)
    db.session.commit()

    # Enviar a cartografo
    if p.cartographer_user_id:
        cart = User.query.get(p.cartographer_user_id)
        db.session.add(Notification(
            user_id=p.cartographer_user_id, title='Nueva visita asignada',
            message=f'Proyecto {p.name} ({p.tracking_id}) asignado para levantamiento.',
            notif_type='task', link=url_for('cartography.project_detail', project_id=p.id)))
        db.session.commit()
        if cart and cart.email:
            email_service.send(cart.email, f'Nueva visita: {p.name}',
                               f'<p>Se te asignó el proyecto <b>{p.name}</b> '
                               f'(ID {p.tracking_id}) para levantamiento cartográfico.</p>')

    flash(f'Proyecto creado con ID {p.tracking_id} y enviado a cartografía.', 'success')
    return redirect(url_for('executive.dashboard'))


@executive_bp.route('/budget/<int:project_id>', methods=['POST'])
@login_required
def release_budget(project_id):
    """Calcula valor por cliente y libera a Gerencia."""
    p = Project.query.get_or_404(project_id)
    total = request.form.get('total_value', type=float) or 0.0
    p.total_value = total
    p.estimated_cost = total

    # Potencial corto + largo plazo (suma de nodos) o el potencial general
    short = sum((n.potential_clients_short or 0) for n in p.nodes)
    long_ = sum((n.potential_clients_long or 0) for n in p.nodes)
    denom = (short + long_) or p.potential_clients or 1
    p.value_per_client = round(total / denom, 2)

    if request.form.get('release') == '1':
        p.manager_status = 'pending_approval'
        p.status = 'pending_manager'
        p.stage = '5. Gerencia'
        p.phase = 'approval'
        p.approval_start_at = datetime.utcnow()
        # Notificar a gerentes
        for mgr in User.query.filter_by(role='manager').all():
            db.session.add(Notification(
                user_id=mgr.id, title='Proyecto liberado a Gerencia',
                message=f'{p.name} ({p.tracking_id}) liberado para aprobación. '
                        f'Valor total ${total:,.0f}.',
                notif_type='alert', link=url_for('manager.dashboard')))
        flash(f'Presupuesto liberado a Gerencia. Valor/cliente ${p.value_per_client:,.0f}.', 'success')
    else:
        flash(f'Presupuesto guardado. Valor/cliente ${p.value_per_client:,.0f}.', 'success')

    db.session.commit()
    return redirect(url_for('executive.dashboard'))
