"""
manager.py — Rol Gerente
=========================
Bandeja de aprobacion con estados (Pendiente / Aprobado / Rechazado / Devuelto a
revision). Observaciones obligatorias para "Devuelto a revision". Cualquier accion
reporta al Ejecutivo Comercial (EC) por correo.
"""
from datetime import datetime

from flask import (Blueprint, render_template, request, flash, redirect, url_for)
from flask_login import login_required, current_user

from app import db
from app.models.core import Project
from app.models.notification import Notification
from app.models.tracking import MANAGER_STATUS_OPTIONS
from app.services.email import email_service

manager_bp = Blueprint('manager', __name__, url_prefix='/manager')


def _guard():
    return current_user.is_superadmin or current_user.role in ('manager', 'admin')


def _aggregate(p):
    """Trae la informacion de procesos anteriores para mostrar en cada proyecto."""
    short = sum((n.potential_clients_short or 0) for n in p.nodes)
    long_ = sum((n.potential_clients_long or 0) for n in p.nodes)
    immediate = short or p.potential_clients or 0
    future = long_
    total_clients = immediate + future
    ratio = round((p.total_value or 0) / total_clients, 2) if total_clients else 0
    return {
        'tracking_id': p.tracking_id or f'#{p.id}',
        'base_address': p.base_address or p.address or '—',
        'municipality': p.municipality or '—',
        'malla': p.malla or '—',
        'executive': p.commercial.full_name if p.commercial else '—',
        'total_value': p.total_value or 0,
        'clients_immediate': immediate,
        'clients_future': future,
        'clients_total': total_clients,
        'ratio': ratio,
    }


@manager_bp.route('/dashboard')
@login_required
def dashboard():
    if not _guard():
        flash('Acceso no autorizado', 'error')
        return redirect(url_for('main.index'))

    status_filter = request.args.get('status', 'pending_approval')
    query = Project.query.filter(Project.status.in_(('pending_manager', 'pending_approval')))
    if status_filter and status_filter != 'all':
        query = Project.query.filter_by(manager_status=status_filter)\
            .filter(Project.stage == '5. Gerencia')
    projects = query.order_by(Project.updated_at.desc()).all()

    rows = [{'project': p, 'agg': _aggregate(p)} for p in projects]
    return render_template('manager/dashboard.html', rows=rows,
                           status_options=MANAGER_STATUS_OPTIONS,
                           status_filter=status_filter)


@manager_bp.route('/decide/<int:project_id>', methods=['POST'])
@login_required
def decide(project_id):
    """Aprobar / Rechazar / Devolver a revision. Reporta al EC por correo."""
    if not _guard():
        flash('Acceso no autorizado', 'error')
        return redirect(url_for('main.index'))

    p = Project.query.get_or_404(project_id)
    decision = request.form.get('decision')  # approved | rejected | returned
    obs = (request.form.get('observations') or '').strip()

    if decision == 'returned' and not obs:
        flash('Las observaciones son obligatorias para devolver a revisión.', 'error')
        return redirect(url_for('manager.dashboard'))

    p.manager_observations = obs
    p.manager_comment = obs
    valid = {o['key'] for o in MANAGER_STATUS_OPTIONS}
    if decision not in valid:
        flash('Decisión inválida.', 'error')
        return redirect(url_for('manager.dashboard'))

    p.manager_status = decision
    if decision == 'approved':
        p.status = 'approved'
        p.manager_approval_status = 'approved'
        p.stage = '6. Ejecución'
        p.phase = 'execution'
        p.execution_start_at = datetime.utcnow()
        # Correo automático con solicitud de máscara (arranca contador ANS)
        p.mask_request_sent_at = datetime.utcnow()
        import os as _os
        mask_email = _os.environ.get('MASK_AREA_EMAIL', _os.environ.get('PDI_AREA_EMAIL', 'proyectos@vanti.com'))
        email_service.send(
            mask_email, f'Solicitud de máscara — {p.name} (ID {p.tracking_id or p.id})',
            f'<h3>Solicitud de máscara</h3>'
            f'<p>Proyecto <b>{p.name}</b> aprobado por Gerencia.</p>'
            f'<p><b>Fecha de envío:</b> {p.mask_request_sent_at.strftime("%Y-%m-%d %H:%M")}</p>'
            f'<p><b>Municipio:</b> {p.municipality or "—"} · <b>Malla:</b> {p.malla or "—"} · '
            f'<b>Valor total:</b> ${(p.total_value or 0):,.0f}</p>'
            f'<p>Se solicita el número de máscara para carga en SAP. El ANS empieza a contar desde esta fecha.</p>')
        label = 'APROBADO'
    elif decision == 'rejected':
        p.status = 'rejected'
        p.manager_approval_status = 'rejected'
        label = 'RECHAZADO'
    else:  # returned
        p.status = 'pending_review'
        p.manager_approval_status = 'pending'
        p.stage = '3. Informe Técnico'
        p.phase = 'viability'
        label = 'DEVUELTO A REVISIÓN'

    # Reportar al Ejecutivo Comercial
    if p.commercial:
        db.session.add(Notification(
            user_id=p.commercial.id, title=f'Gerencia: {label}',
            message=f'El proyecto {p.name} ({p.tracking_id or p.id}) fue marcado como {label}.'
                    + (f' Obs: {obs}' if obs else ''),
            notif_type='success' if decision == 'approved' else 'warning',
            link=url_for('executive.dashboard')))
        db.session.commit()
        if p.commercial.email:
            email_service.send(
                p.commercial.email, f'Decisión Gerencial: {p.name} — {label}',
                f'<h3>{label}</h3><p>Proyecto <b>{p.name}</b> (ID {p.tracking_id or p.id}).</p>'
                + (f'<p><b>Observaciones:</b> {obs}</p>' if obs else ''))
    else:
        db.session.commit()

    flash(f'Proyecto {p.name}: {label}.', 'success')
    return redirect(url_for('manager.dashboard'))
