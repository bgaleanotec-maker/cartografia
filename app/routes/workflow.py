"""
workflow.py — Rutas para gestión de flujos de trabajo y ANS
"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models.workflow import (
    WorkflowTask, WORKFLOW_DEFINITIONS,
    create_workflow_for_project
)
from app.models.core import Project
from app.models.user import User
from datetime import datetime

workflow_bp = Blueprint('workflow', __name__, url_prefix='/workflow')


@workflow_bp.route('/')
@login_required
def index():
    """Vista principal de flujos — muestra tareas según rol del usuario."""
    role = request.args.get('role', '')

    # Determinar qué flujos puede ver el usuario
    if current_user.role == 'superadmin' or current_user.is_superadmin:
        visible_roles = ['cartography', 'projects', 'executive']
    elif current_user.role == 'cartography':
        visible_roles = ['cartography']
    elif current_user.role == 'projects':
        visible_roles = ['projects']
    elif current_user.role in ('executive', 'manager'):
        visible_roles = ['executive']
    else:
        visible_roles = ['cartography', 'projects', 'executive']

    if role and role in visible_roles:
        visible_roles = [role]

    # Obtener proyectos con tareas de workflow
    projects = Project.query.order_by(Project.created_at.desc()).all()

    # Obtener tareas agrupadas por proyecto y rol
    tasks_by_project = {}
    for proj in projects:
        tasks = WorkflowTask.query.filter_by(project_id=proj.id)\
            .filter(WorkflowTask.workflow_role.in_(visible_roles))\
            .order_by(WorkflowTask.step_order).all()
        if tasks:
            # Actualizar semaforo ANS
            for t in tasks:
                t.update_ans_status()
            db.session.commit()
            tasks_by_project[proj] = tasks

    # Estadísticas
    total_tasks = WorkflowTask.query.filter(
        WorkflowTask.workflow_role.in_(visible_roles)).count()
    pending = WorkflowTask.query.filter(
        WorkflowTask.workflow_role.in_(visible_roles),
        WorkflowTask.status == 'pending').count()
    in_progress = WorkflowTask.query.filter(
        WorkflowTask.workflow_role.in_(visible_roles),
        WorkflowTask.status == 'in_progress').count()
    completed = WorkflowTask.query.filter(
        WorkflowTask.workflow_role.in_(visible_roles),
        WorkflowTask.status.in_(['completed', 'approved'])).count()
    overdue = WorkflowTask.query.filter(
        WorkflowTask.workflow_role.in_(visible_roles),
        WorkflowTask.ans_status == 'expired').count()

    stats = {
        'total': total_tasks,
        'pending': pending,
        'in_progress': in_progress,
        'completed': completed,
        'overdue': overdue
    }

    return render_template('workflow/index.html',
                           tasks_by_project=tasks_by_project,
                           stats=stats,
                           visible_roles=visible_roles,
                           definitions=WORKFLOW_DEFINITIONS,
                           current_role_filter=role)


@workflow_bp.route('/project/<int:project_id>/init', methods=['POST'])
@login_required
def init_workflow(project_id):
    """Inicializar flujos de trabajo para un proyecto."""
    project = Project.query.get_or_404(project_id)
    role = request.form.get('role', 'cartography')

    # Verificar que no existan ya tareas para este rol
    existing = WorkflowTask.query.filter_by(
        project_id=project_id, workflow_role=role).first()
    if existing:
        flash(f'El flujo de {role} ya existe para este proyecto.', 'warning')
        return redirect(url_for('workflow.index'))

    tasks = create_workflow_for_project(
        project_id, role, assigned_to_id=current_user.id)
    flash(f'Flujo {role} creado con {len(tasks)} pasos.', 'success')
    return redirect(url_for('workflow.project_detail', project_id=project_id))


@workflow_bp.route('/project/<int:project_id>/init-all', methods=['POST'])
@login_required
def init_all_workflows(project_id):
    """Inicializar los 3 flujos para un proyecto."""
    project = Project.query.get_or_404(project_id)
    total = 0
    for role in ['cartography', 'projects', 'executive']:
        existing = WorkflowTask.query.filter_by(
            project_id=project_id, workflow_role=role).first()
        if not existing:
            tasks = create_workflow_for_project(project_id, role)
            total += len(tasks)
    flash(f'Flujos completos creados: {total} tareas totales.', 'success')
    return redirect(url_for('workflow.project_detail', project_id=project_id))


@workflow_bp.route('/project/<int:project_id>')
@login_required
def project_detail(project_id):
    """Ver flujo completo de un proyecto."""
    project = Project.query.get_or_404(project_id)

    cart_tasks = WorkflowTask.query.filter_by(
        project_id=project_id, workflow_role='cartography')\
        .order_by(WorkflowTask.step_order).all()
    proj_tasks = WorkflowTask.query.filter_by(
        project_id=project_id, workflow_role='projects')\
        .order_by(WorkflowTask.step_order).all()
    exec_tasks = WorkflowTask.query.filter_by(
        project_id=project_id, workflow_role='executive')\
        .order_by(WorkflowTask.step_order).all()

    # Actualizar ANS
    for t in cart_tasks + proj_tasks + exec_tasks:
        t.update_ans_status()
    db.session.commit()

    # Calcular progreso por rol
    def calc_progress(tasks):
        if not tasks:
            return 0
        done = sum(1 for t in tasks if t.status in ('completed', 'approved'))
        return round(done / len(tasks) * 100)

    users = User.query.filter_by(is_active=True).all()

    return render_template('workflow/project_detail.html',
                           project=project,
                           cart_tasks=cart_tasks,
                           proj_tasks=proj_tasks,
                           exec_tasks=exec_tasks,
                           cart_progress=calc_progress(cart_tasks),
                           proj_progress=calc_progress(proj_tasks),
                           exec_progress=calc_progress(exec_tasks),
                           users=users)


@workflow_bp.route('/task/<int:task_id>/start', methods=['POST'])
@login_required
def start_task(task_id):
    """Iniciar una tarea."""
    task = WorkflowTask.query.get_or_404(task_id)
    task.start()
    task.assigned_to_id = task.assigned_to_id or current_user.id
    db.session.commit()
    return jsonify({'ok': True, 'status': task.status, 'ans_status': task.ans_status})


@workflow_bp.route('/task/<int:task_id>/complete', methods=['POST'])
@login_required
def complete_task(task_id):
    """Completar una tarea."""
    task = WorkflowTask.query.get_or_404(task_id)
    notes = request.form.get('notes', '') or request.json.get('notes', '') if request.is_json else ''
    if notes:
        task.notes = (task.notes or '') + f'\n[{datetime.utcnow().strftime("%Y-%m-%d %H:%M")}] {notes}'

    if task.requires_approval:
        task.status = 'waiting_approval'
    else:
        task.complete()

    db.session.commit()
    return jsonify({'ok': True, 'status': task.status})


@workflow_bp.route('/task/<int:task_id>/approve', methods=['POST'])
@login_required
def approve_task(task_id):
    """Aprobar una tarea."""
    task = WorkflowTask.query.get_or_404(task_id)
    task.approve(current_user.id)
    db.session.commit()
    return jsonify({'ok': True, 'status': task.status})


@workflow_bp.route('/task/<int:task_id>/reject', methods=['POST'])
@login_required
def reject_task(task_id):
    """Rechazar una tarea con razon."""
    data = request.json or request.form
    reason = data.get('reason', 'Sin razon especificada')
    task = WorkflowTask.query.get_or_404(task_id)
    task.reject(reason, current_user.id)
    db.session.commit()
    return jsonify({
        'ok': True,
        'status': task.status,
        'rejection_count': task.rejection_count,
        'new_deadline': task.deadline_at.isoformat() if task.deadline_at else None
    })


@workflow_bp.route('/task/<int:task_id>/assign', methods=['POST'])
@login_required
def assign_task(task_id):
    """Asignar tarea a un usuario."""
    data = request.json or request.form
    user_id = data.get('user_id')
    task = WorkflowTask.query.get_or_404(task_id)
    task.assigned_to_id = int(user_id) if user_id else None
    db.session.commit()
    return jsonify({'ok': True})


@workflow_bp.route('/task/<int:task_id>/notes', methods=['POST'])
@login_required
def add_notes(task_id):
    """Agregar notas a una tarea."""
    data = request.json or request.form
    note = data.get('notes', '')
    task = WorkflowTask.query.get_or_404(task_id)
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    task.notes = (task.notes or '') + f'\n[{timestamp} - {current_user.full_name}] {note}'
    db.session.commit()
    return jsonify({'ok': True, 'notes': task.notes})
