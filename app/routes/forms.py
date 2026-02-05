from flask import Blueprint, jsonify, request, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from app.models.core import FormTemplate, FormField, FormSubmission, Project, db
import json

forms_bp = Blueprint('forms', __name__, url_prefix='/forms')

# --- Admin Routes (Templates) ---

@forms_bp.route('/templates')
@login_required
def list_templates():
    if current_user.role != 'admin':
        return redirect(url_for('main.index'))
    templates = FormTemplate.query.all()
    return render_template('admin/form_templates.html', templates=templates)

@forms_bp.route('/templates/create', methods=['POST'])
@login_required
def create_template():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    data = request.json
    template = FormTemplate(
        name=data.get('name'),
        description=data.get('description'),
        hook=data.get('hook'),
        role_access=data.get('role_access')
    )
    db.session.add(template)
    db.session.commit()
    return jsonify({'status': 'success', 'id': template.id})

@forms_bp.route('/templates/<int:id>/fields', methods=['POST'])
@login_required
def add_field(id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    data = request.json
    field = FormField(
        template_id=id,
        label=data.get('label'),
        field_type=data.get('field_type'),
        options=json.dumps(data.get('options', [])),
        required=data.get('required', False),
        sequence=data.get('sequence', 0)
    )
    db.session.add(field)
    db.session.commit()
    return jsonify({'status': 'success', 'id': field.id})

# --- User Routes (Submissions) ---

@forms_bp.route('/project/<int:project_id>/submit/<int:template_id>', methods=['POST'])
@login_required
def submit_form(project_id, template_id):
    project = Project.query.get_or_404(project_id)
    template = FormTemplate.query.get_or_404(template_id)
    
    # Check permissions (basic)
    if template.role_access and current_user.role != template.role_access and current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized role'}), 403

    data = request.json
    
    submission = FormSubmission(
        project_id=project.id,
        form_template_id=template.id,
        user_id=current_user.id,
        data=json.dumps(data)
    )
    db.session.add(submission)
    db.session.commit()
    
    return jsonify({'status': 'success', 'id': submission.id})
