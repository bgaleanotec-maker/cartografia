"""
SuperAdmin Blueprint
====================
Acceso exclusivo para usuarios con is_superadmin=True.
Gestiona: usuarios (todos los roles), notificaciones, proyectos, sistema.
"""
import secrets
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models.user import User, ROLES
from app.models.notification import Notification
from app.models.core import Project

superadmin_bp = Blueprint('superadmin', __name__, url_prefix='/superadmin')


# ── Guard ──────────────────────────────────────────────────────────────────────
@superadmin_bp.before_request
@login_required
def require_superadmin():
    if not current_user.is_superadmin:
        flash('Acceso restringido a Super Administradores.', 'error')
        return redirect(url_for('main.index'))


# ── Dashboard ──────────────────────────────────────────────────────────────────
@superadmin_bp.route('/')
def dashboard():
    stats = {
        'users':         User.query.count(),
        'active_users':  User.query.filter_by(is_active=True).count(),
        'projects':      Project.query.count(),
        'notifications': Notification.query.count(),
        'unread_notifs': Notification.query.filter_by(read=False).count(),
        'by_phase': {
            phase: Project.query.filter_by(phase=phase).count()
            for phase in ('prospecting', 'cartography', 'viability', 'approval', 'execution', 'finished')
        },
        'by_role': {
            role: User.query.filter_by(role=role).count()
            for role in ROLES
        }
    }
    recent_users  = User.query.order_by(User.created_at.desc()).limit(8).all()
    recent_notifs = Notification.query.order_by(Notification.created_at.desc()).limit(10).all()
    return render_template('superadmin/dashboard.html',
                           stats=stats,
                           recent_users=recent_users,
                           recent_notifs=recent_notifs,
                           roles=ROLES)


# ── Users ──────────────────────────────────────────────────────────────────────
@superadmin_bp.route('/users')
def users():
    role_filter = request.args.get('role', '')
    search      = request.args.get('q', '').strip()
    query = User.query
    if role_filter:
        query = query.filter_by(role=role_filter)
    if search:
        query = query.filter(
            db.or_(User.username.ilike(f'%{search}%'),
                   User.email.ilike(f'%{search}%'),
                   User.full_name.ilike(f'%{search}%'))
        )
    all_users = query.order_by(User.is_superadmin.desc(), User.created_at.desc()).all()
    return render_template('superadmin/users.html',
                           users=all_users,
                           roles=ROLES,
                           role_filter=role_filter,
                           search=search)


@superadmin_bp.route('/users/create', methods=['POST'])
def create_user():
    data = request.form
    username = data.get('username', '').strip()
    email    = data.get('email', '').strip() or None
    password = data.get('password', '')
    role     = data.get('role', 'commercial')
    full_name = data.get('full_name', '').strip() or None
    is_super = data.get('is_superadmin') == '1'

    if not username or not password:
        flash('Usuario y contraseña son obligatorios.', 'error')
        return redirect(url_for('superadmin.users'))

    if User.query.filter_by(username=username).first():
        flash(f'El usuario "{username}" ya existe.', 'error')
        return redirect(url_for('superadmin.users'))

    if email and User.query.filter_by(email=email).first():
        flash('El email ya está en uso.', 'error')
        return redirect(url_for('superadmin.users'))

    user = User(
        username=username, email=email,
        role=role, full_name=full_name,
        is_superadmin=is_super, is_active=True
    )
    user.set_password(password)
    # Generar API key automáticamente
    user.api_key = secrets.token_hex(24)
    db.session.add(user)
    db.session.commit()
    flash(f'Usuario {username} creado con rol {role}.', 'success')
    return redirect(url_for('superadmin.users'))


@superadmin_bp.route('/users/<int:user_id>/edit', methods=['POST'])
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    data = request.form

    # No permitir degradar el único superadmin si el cambio viene del exterior
    if user.is_superadmin and not current_user.is_superadmin:
        flash('No tienes permiso para editar un superadmin.', 'error')
        return redirect(url_for('superadmin.users'))

    username  = data.get('username', '').strip()
    email     = data.get('email', '').strip() or None
    full_name = data.get('full_name', '').strip() or None
    role      = data.get('role', user.role)
    password  = data.get('password', '').strip()
    is_active = data.get('is_active') == '1'
    is_super  = data.get('is_superadmin') == '1'

    # Unique checks
    dup_user = User.query.filter_by(username=username).first()
    if dup_user and dup_user.id != user_id:
        flash('Ese nombre de usuario ya existe.', 'error')
        return redirect(url_for('superadmin.users'))

    if email:
        dup_email = User.query.filter_by(email=email).first()
        if dup_email and dup_email.id != user_id:
            flash('Ese email ya está en uso.', 'error')
            return redirect(url_for('superadmin.users'))

    user.username      = username
    user.email         = email
    user.full_name     = full_name
    user.role          = role
    user.is_active     = is_active
    user.is_superadmin = is_super
    if password:
        user.set_password(password)

    db.session.commit()
    flash(f'Usuario {username} actualizado.', 'success')
    return redirect(url_for('superadmin.users'))


@superadmin_bp.route('/users/<int:user_id>/toggle', methods=['POST'])
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_superadmin and user.id != current_user.id:
        return jsonify({'error': 'No se puede desactivar un superadmin desde aquí.'}), 403
    user.is_active = not user.is_active
    db.session.commit()
    return jsonify({'status': 'ok', 'is_active': user.is_active})


@superadmin_bp.route('/users/<int:user_id>/regenerate-key', methods=['POST'])
def regenerate_api_key(user_id):
    user = User.query.get_or_404(user_id)
    user.api_key = secrets.token_hex(24)
    db.session.commit()
    return jsonify({'status': 'ok', 'api_key': user.api_key})


@superadmin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_superadmin:
        flash('No se puede eliminar un superadmin.', 'error')
        return redirect(url_for('superadmin.users'))
    if user.id == current_user.id:
        flash('No puedes eliminarte a ti mismo.', 'error')
        return redirect(url_for('superadmin.users'))
    db.session.delete(user)
    db.session.commit()
    flash(f'Usuario {user.username} eliminado.', 'success')
    return redirect(url_for('superadmin.users'))


# ── Notifications ──────────────────────────────────────────────────────────────
@superadmin_bp.route('/notifications')
def notifications():
    all_notifs = Notification.query.order_by(Notification.created_at.desc()).limit(200).all()
    all_users  = User.query.filter_by(is_active=True).order_by(User.username).all()
    return render_template('superadmin/notifications.html',
                           notifications=all_notifs,
                           users=all_users)


@superadmin_bp.route('/notifications/send', methods=['POST'])
def send_notification():
    """SuperAdmin envía notificación manual a un usuario o a todos."""
    data       = request.form
    target     = data.get('target')   # 'all' o user_id
    title      = data.get('title', '').strip()
    message    = data.get('message', '').strip()
    notif_type = data.get('type', 'info')
    link       = data.get('link', '').strip() or None

    if not title:
        flash('El título es obligatorio.', 'error')
        return redirect(url_for('superadmin.notifications'))

    if target == 'all':
        users = User.query.filter_by(is_active=True).all()
        for u in users:
            n = Notification(
                user_id=u.id, title=title, message=message,
                notif_type=notif_type, link=link,
                source_project='admin', created_by_id=current_user.id
            )
            db.session.add(n)
        db.session.commit()
        flash(f'Notificación enviada a {len(users)} usuarios.', 'success')
    else:
        try:
            uid = int(target)
        except (TypeError, ValueError):
            flash('Usuario inválido.', 'error')
            return redirect(url_for('superadmin.notifications'))
        n = Notification(
            user_id=uid, title=title, message=message,
            notif_type=notif_type, link=link,
            source_project='admin', created_by_id=current_user.id
        )
        db.session.add(n)
        db.session.commit()
        flash('Notificación enviada.', 'success')

    return redirect(url_for('superadmin.notifications'))


@superadmin_bp.route('/notifications/<int:notif_id>/delete', methods=['POST'])
def delete_notification(notif_id):
    n = Notification.query.get_or_404(notif_id)
    db.session.delete(n)
    db.session.commit()
    return jsonify({'status': 'ok'})


@superadmin_bp.route('/notifications/clear-read', methods=['POST'])
def clear_read_notifications():
    Notification.query.filter_by(read=True).delete()
    db.session.commit()
    flash('Notificaciones leídas eliminadas.', 'success')
    return redirect(url_for('superadmin.notifications'))
