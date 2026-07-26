from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from app.models.user import User
from app.models.core import Project
from app.models.notification import Notification
from app.models.tracking import STAGE_OPTIONS, MANAGER_STATUS_OPTIONS, ActivityType
from app import db
from werkzeug.security import generate_password_hash

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.before_request
@login_required
def require_admin():
    if not (current_user.is_superadmin or current_user.role in ('admin', 'superadmin')):
        flash('Acceso no autorizado.', 'error')
        return redirect(url_for('main.index'))


@admin_bp.route('/panel')
def panel():
    """Panel del administrador: carga masiva, usuarios, estados y reasignación EC."""
    executives = User.query.filter(User.role.in_(('commercial', 'executive'))).all()
    stats = {
        'projects': Project.query.count(),
        'users': User.query.count(),
        'executives': len(executives),
    }
    # Conteo de proyectos por ejecutivo (para reasignación)
    exec_counts = {e.id: Project.query.filter_by(commercial_user_id=e.id).count() for e in executives}
    return render_template('admin/panel.html', executives=executives, stats=stats,
                           exec_counts=exec_counts, stage_options=STAGE_OPTIONS,
                           manager_status_options=MANAGER_STATUS_OPTIONS)


@admin_bp.route('/reassign', methods=['POST'])
def reassign_projects():
    """Reasigna proyectos de un ejecutivo comercial a otro (vacaciones/temporadas)."""
    from_id = request.form.get('from_executive', type=int)
    to_id = request.form.get('to_executive', type=int)
    if not from_id or not to_id or from_id == to_id:
        flash('Selecciona dos ejecutivos distintos.', 'error')
        return redirect(url_for('admin.panel'))

    to_user = User.query.get_or_404(to_id)
    projects = Project.query.filter_by(commercial_user_id=from_id).all()
    for p in projects:
        p.commercial_user_id = to_id
    db.session.commit()

    if to_user.email and projects:
        from app.services.email import email_service
        email_service.send(to_user.email, 'Proyectos reasignados',
                           f'<p>Se te reasignaron {len(projects)} proyectos.</p>')
    flash(f'{len(projects)} proyectos reasignados a {to_user.full_name or to_user.username}.', 'success')
    return redirect(url_for('admin.panel'))


@admin_bp.route('/activity-types', methods=['GET', 'POST'])
def activity_types():
    """Catálogo PARAMETRIZABLE de tipos de actividad para la bitácora."""
    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        if name and not ActivityType.query.filter_by(name=name).first():
            db.session.add(ActivityType(name=name,
                                        description=request.form.get('description'), active=True))
            db.session.commit()
            flash(f'Actividad "{name}" agregada al catálogo.', 'success')
        else:
            flash('Nombre vacío o ya existe.', 'error')
        return redirect(url_for('admin.activity_types'))
    types = ActivityType.query.order_by(ActivityType.name).all()
    return render_template('admin/activity_types.html', types=types)


@admin_bp.route('/activity-types/<int:type_id>/toggle', methods=['POST'])
def toggle_activity_type(type_id):
    t = ActivityType.query.get_or_404(type_id)
    t.active = not t.active
    db.session.commit()
    flash(f'"{t.name}" {"activada" if t.active else "desactivada"}.', 'success')
    return redirect(url_for('admin.activity_types'))


@admin_bp.route('/activity-types/<int:type_id>/delete', methods=['POST'])
def delete_activity_type(type_id):
    t = ActivityType.query.get_or_404(type_id)
    db.session.delete(t)
    db.session.commit()
    flash('Tipo de actividad eliminado.', 'success')
    return redirect(url_for('admin.activity_types'))


@admin_bp.route('/project/<int:project_id>/state', methods=['POST'])
def change_state(project_id):
    """Cambio/modificación manual de estados por el administrador."""
    p = Project.query.get_or_404(project_id)
    stage = request.form.get('stage')
    mstatus = request.form.get('manager_status')
    if stage:
        p.stage = stage
    if mstatus:
        p.manager_status = mstatus
    db.session.commit()
    flash(f'Estado de {p.name} actualizado.', 'success')
    return redirect(request.referrer or url_for('admin.panel'))

@admin_bp.route('/users')
def users():
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@admin_bp.route('/users/create', methods=['POST'])
def create_user():
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    role = request.form.get('role')

    if User.query.filter_by(username=username).first():
        flash('El nombre de usuario ya existe.', 'error')
        return redirect(url_for('admin.users'))
    
    if User.query.filter_by(email=email).first():
        flash('El correo electrónico ya existe.', 'error')
        return redirect(url_for('admin.users'))

    user = User(username=username, email=email, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    
    flash('Usuario creado exitosamente.', 'success')
    return redirect(url_for('admin.users'))

@admin_bp.route('/users/delete/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if user_id == current_user.id:
        flash('No puedes eliminar tu propio usuario.', 'error')
        return redirect(url_for('admin.users'))

    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash(f'Usuario {user.username} eliminado.', 'success')
    return redirect(url_for('admin.users'))

@admin_bp.route('/users/edit/<int:user_id>', methods=['POST'])
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    
    username = request.form.get('username')
    email = request.form.get('email')
    role = request.form.get('role')
    password = request.form.get('password')

    # Basic validation
    existing_user = User.query.filter_by(username=username).first()
    if existing_user and existing_user.id != user.id:
        flash('El nombre de usuario ya existe.', 'error')
        return redirect(url_for('admin.users'))
        
    existing_email = User.query.filter_by(email=email).first()
    if existing_email and existing_email.id != user.id:
        flash('El correo electrónico ya existe.', 'error')
        return redirect(url_for('admin.users'))

    user.username = username
    user.email = email
    user.role = role
    
    if password:
        user.set_password(password)
        
    db.session.commit()
    flash('Usuario actualizado correctamente.', 'success')
    return redirect(url_for('admin.users'))
