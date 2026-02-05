from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from app.models.user import User
from app import db
from werkzeug.security import generate_password_hash

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.before_request
@login_required
def require_admin():
    if current_user.role != 'admin':
        flash('Acceso no autorizado.', 'error')
        return redirect(url_for('main.index'))

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
        
    flash('Usuario eliminado.', 'success')
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
    flash('Usuario actualizado correctly.', 'success')
    return redirect(url_for('admin.users'))
