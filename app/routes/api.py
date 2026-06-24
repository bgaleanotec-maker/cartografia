from flask import Blueprint, request, jsonify
from app import db
from app.models.core import Project, Visit, ProjectNode, ProjectDocument
from app.models.user import User
from app.models.notification import Notification, NOTIF_TYPES
from flask_login import current_user
import json
import os
from functools import wraps
from werkzeug.utils import secure_filename
from datetime import datetime

from app.services.document_service import document_service

api_bp = Blueprint('api', __name__)


# ══════════════════════════════════════════════════════════════════════════════
# API KEY AUTH DECORATOR
# ══════════════════════════════════════════════════════════════════════════════
def require_api_key(f):
    """
    Decorator: permite acceso a endpoints si se provee una api_key válida
    de cualquier usuario del sistema (en Header X-API-Key o query ?api_key=).
    Útil para integración entre proyectos (Doctor, otros).
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        key = (request.headers.get('X-API-Key') or
               request.args.get('api_key') or
               (request.json or {}).get('api_key') if request.is_json else None)
        if not key:
            return jsonify({'error': 'API key requerida.'}), 401
        user = User.query.filter_by(api_key=key, is_active=True).first()
        if not user:
            return jsonify({'error': 'API key inválida o usuario inactivo.'}), 403
        # Inyectar el caller en el request context
        request.api_caller = user
        return f(*args, **kwargs)
    return decorated


# ══════════════════════════════════════════════════════════════════════════════
# NOTIFICATIONS API — integración cross-proyectos
# ══════════════════════════════════════════════════════════════════════════════

@api_bp.route('/notifications/push', methods=['POST'])
@require_api_key
def push_notification():
    """
    Endpoint para que otros proyectos empujen notificaciones.

    Body JSON:
    {
        "api_key": "...",             # o en Header X-API-Key
        "target_username": "...",     # username del destinatario
        "title": "...",
        "message": "...",             # opcional
        "type": "info|success|warning|error|task|alert",
        "source_project": "doctor",   # nombre del proyecto origen
        "link": "https://..."         # URL opcional a abrir al hacer clic
    }

    Ejemplo desde Doctor (Python):
        import requests
        requests.post('https://tuapp.com/api/notifications/push',
            headers={'X-API-Key': 'tu_api_key'},
            json={
                'target_username': 'bgaleanotec',
                'title': 'Nuevo paciente asignado',
                'type': 'task',
                'source_project': 'doctor',
                'link': 'https://doctor.app/paciente/42'
            })
    """
    data = request.get_json(silent=True) or {}

    target_username = data.get('target_username')
    title           = (data.get('title') or '').strip()
    message         = (data.get('message') or '').strip() or None
    notif_type      = data.get('type', 'info')
    source          = (data.get('source_project') or 'external').strip()
    link            = (data.get('link') or '').strip() or None

    # Validaciones
    if not target_username:
        return jsonify({'error': 'target_username es obligatorio.'}), 400
    if not title:
        return jsonify({'error': 'title es obligatorio.'}), 400
    if notif_type not in NOTIF_TYPES:
        notif_type = 'info'

    target_user = User.query.filter_by(username=target_username, is_active=True).first()
    if not target_user:
        return jsonify({'error': f'Usuario "{target_username}" no encontrado.'}), 404

    notif = Notification(
        user_id        = target_user.id,
        title          = title,
        message        = message,
        notif_type     = notif_type,
        source_project = source,
        link           = link,
        created_by_id  = request.api_caller.id
    )
    db.session.add(notif)
    db.session.commit()

    return jsonify({
        'status':  'ok',
        'id':      notif.id,
        'message': f'Notificación enviada a {target_username}.'
    }), 201


@api_bp.route('/notifications/push/broadcast', methods=['POST'])
@require_api_key
def push_broadcast():
    """
    Envía la misma notificación a múltiples usuarios (por username o por rol).

    Body JSON:
    {
        "api_key": "...",
        "targets": ["user1", "user2"],   # lista de usernames
        "roles":   ["commercial"],        # alternativa: por rol
        "title": "...",
        "type":  "info",
        "source_project": "doctor"
    }
    """
    data  = request.get_json(silent=True) or {}
    title = (data.get('title') or '').strip()
    if not title:
        return jsonify({'error': 'title es obligatorio.'}), 400

    notif_type = data.get('type', 'info')
    if notif_type not in NOTIF_TYPES:
        notif_type = 'info'

    source  = (data.get('source_project') or 'external').strip()
    message = (data.get('message') or '').strip() or None
    link    = (data.get('link') or '').strip() or None

    users_set = set()

    # Por username
    for uname in (data.get('targets') or []):
        u = User.query.filter_by(username=uname, is_active=True).first()
        if u:
            users_set.add(u)

    # Por rol
    for role in (data.get('roles') or []):
        for u in User.query.filter_by(role=role, is_active=True).all():
            users_set.add(u)

    if not users_set:
        return jsonify({'error': 'No se encontraron destinatarios válidos.'}), 404

    count = 0
    for u in users_set:
        n = Notification(
            user_id=u.id, title=title, message=message,
            notif_type=notif_type, source_project=source,
            link=link, created_by_id=request.api_caller.id
        )
        db.session.add(n)
        count += 1

    db.session.commit()
    return jsonify({'status': 'ok', 'sent_to': count}), 201


@api_bp.route('/notifications/my', methods=['GET'])
def my_notifications():
    """
    Retorna las notificaciones del usuario actual (requiere sesión web).
    Usada por el dropdown del navbar.
    """
    if not current_user.is_authenticated:
        return jsonify({'error': 'No autenticado.'}), 401

    limit  = min(int(request.args.get('limit', 20)), 50)
    unread_only = request.args.get('unread') == '1'

    q = current_user.notifications.order_by(Notification.created_at.desc())
    if unread_only:
        q = q.filter_by(read=False)
    notifs = q.limit(limit).all()

    return jsonify({
        'unread_count': current_user.unread_count,
        'notifications': [n.to_dict() for n in notifs]
    })


@api_bp.route('/notifications/<int:notif_id>/read', methods=['POST'])
def mark_notification_read(notif_id):
    """Marca una notificación como leída."""
    if not current_user.is_authenticated:
        return jsonify({'error': 'No autenticado.'}), 401
    notif = Notification.query.get_or_404(notif_id)
    if notif.user_id != current_user.id:
        return jsonify({'error': 'Sin permiso.'}), 403
    notif.mark_read()
    db.session.commit()
    return jsonify({'status': 'ok', 'unread_count': current_user.unread_count})


@api_bp.route('/notifications/read-all', methods=['POST'])
def mark_all_read():
    """Marca todas las notificaciones del usuario como leídas."""
    if not current_user.is_authenticated:
        return jsonify({'error': 'No autenticado.'}), 401
    from datetime import datetime
    current_user.notifications.filter_by(read=False).update(
        {'read': True, 'read_at': datetime.utcnow()}
    )
    db.session.commit()
    return jsonify({'status': 'ok', 'unread_count': 0})


@api_bp.route('/visits/sync', methods=['POST'])
def sync_visit():
    data = request.json
    
    try:
        # Create Project
        nodes_data = data.get('nodes', [])
        center_lat = nodes_data[0]['latitude'] if nodes_data else (data.get('latitude') or 0.0)
        center_lon = nodes_data[0]['longitude'] if nodes_data else (data.get('longitude') or 0.0)

        project = Project(
            name=data.get('name', 'Sin Nombre'),
            address=data.get('address'),
            latitude=float(center_lat),
            longitude=float(center_lon),
            status='prospecting',
            description=data.get('description'),
            commercial_user_id=current_user.id if current_user.is_authenticated else None,
            sla_status='green', # Default start
            viability_status='pending'
        )
        db.session.add(project)
        db.session.commit()
        
        # Create Nodes
        if nodes_data:
            for idx, node in enumerate(nodes_data):
                new_node = ProjectNode(
                    project_id=project.id,
                    latitude=float(node['latitude']),
                    longitude=float(node['longitude']),
                    sequence=idx,
                    manual_length=float(node.get('manual_length', 0)),
                    potential_clients=int(node.get('potential_clients', 0)),
                    gas_points=int(node.get('gas_points', 0)),
                    # New fields
                    has_water_source=node.get('has_water_source', False),
                    is_rocky_ground=node.get('is_rocky_ground', False),
                    observations=node.get('observations', '')
                )
                db.session.add(new_node)
        
        # Create Visit
        visit = Visit(
            project_id=project.id,
            local_id=data.get('local_id'),
            notes=data.get('description'),
            census_data=data.get('census_data'),
            created_by_id=current_user.id if current_user.is_authenticated else None
        )
        db.session.add(visit)
        db.session.commit()
        
        return jsonify({'status': 'success', 'project_id': project.id, 'visit_id': visit.id}), 201
        
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@api_bp.route('/projects/<int:project_id>/upload', methods=['POST'])
def upload_document(project_id):
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    category = request.form.get('category', 'general')
    
    try:
        doc = document_service.save_project_document(file, project_id, category)
        return jsonify({'status': 'success', 'document': doc.to_dict()}), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        print(f"Error uploading document: {e}")
        return jsonify({'error': 'Internal server error during upload'}), 500

@api_bp.route('/projects/documents/<int:doc_id>', methods=['DELETE'])
def delete_document(doc_id):
    try:
        document_service.delete_document(doc_id)
        return jsonify({'status': 'success'})
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        print(f"Error deleting document: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@api_bp.route('/projects/<int:project_id>/viability', methods=['POST'])
def update_viability(project_id):
    data = request.json
    status = data.get('status') # 'viable', 'non_viable'
    
    project = Project.query.get_or_404(project_id)
    project.viability_status = status
    
    # Save estimated cost if provided
    cost = data.get('estimated_cost')
    if cost is not None:
        project.estimated_cost = float(cost)

    if status == 'viable':
        # Escalation Rule: > 50 Million COP requires Manager Approval
        if project.estimated_cost and project.estimated_cost > 50000000:
             project.status = 'pending_manager'
             project.manager_approval_status = 'pending'
        else:
             project.status = 'approved' # Auto-approve low value
             project.sla_status = 'green'
             
    elif status == 'non_viable':
        project.status = 'rejected'
        project.sla_status = 'red'
        
    db.session.commit()
    return jsonify({'status': 'success'})

# --- Node Management APIs ---
@api_bp.route('/projects/<int:project_id>/nodes', methods=['POST'])
def create_node(project_id):
    data = request.json
    project = Project.query.get_or_404(project_id)
    
    # Simple logic: append to end
    new_sequence = len(project.nodes) + 1
    
    node = ProjectNode(
        project_id=project.id,
        latitude=data['latitude'],
        longitude=data['longitude'],
        sequence=new_sequence
    )
    db.session.add(node)
    db.session.commit()
    return jsonify({'status': 'success', 'node': node.to_dict()})

@api_bp.route('/nodes/<int:node_id>', methods=['PUT'])
def update_node(node_id):
    node = ProjectNode.query.get_or_404(node_id)
    data = request.json
    
    if 'latitude' in data: node.latitude = float(data['latitude'])
    if 'longitude' in data: node.longitude = float(data['longitude'])
    
    # Attributes
    if 'has_water_source' in data: node.has_water_source = data['has_water_source']
    if 'is_rocky_ground' in data: node.is_rocky_ground = data['is_rocky_ground']
    if 'observations' in data: node.observations = data['observations']
    if 'potential_clients' in data: node.potential_clients = int(data.get('potential_clients') or 0)
    if 'potential_clients_short' in data: node.potential_clients_short = int(data.get('potential_clients_short') or 0)
    if 'potential_clients_long' in data: node.potential_clients_long = int(data.get('potential_clients_long') or 0)
    if 'gas_points' in data: node.gas_points = int(data.get('gas_points') or 0)
    if 'manual_length' in data: node.manual_length = float(data.get('manual_length') or 0.0)
    if 'terrain_conditions' in data:
        import json as _json
        conds = data.get('terrain_conditions') or []
        node.terrain_conditions = _json.dumps(conds)
        # Mantener flags legacy sincronizados para el mapa
        node.has_water_source = 'ronda_hidraulica' in conds or 'proteccion_ambiental' in conds
        node.is_rocky_ground = any(c.startswith('remocion') for c in conds)

    db.session.commit()
    return jsonify({'status': 'success'})

@api_bp.route('/nodes/<int:node_id>', methods=['DELETE'])
def delete_node(node_id):
    node = ProjectNode.query.get_or_404(node_id)
    db.session.delete(node)
    db.session.commit()
    return jsonify({'status': 'success'})

@api_bp.route('/nodes/<int:node_id>/upload', methods=['POST'])
def upload_node_photo(node_id):
    node = ProjectNode.query.get_or_404(node_id)
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    if file:
        filename = secure_filename(file.filename)
        unique_name = f"node_{node_id}_{int(datetime.now().timestamp())}_{filename}"
        file_path = os.path.join(document_service.upload_folder, unique_name)
        file.save(file_path)
        
        node.photo_url = unique_name
        db.session.commit()
        
        return jsonify({'status': 'success', 'photo_url': unique_name}), 201
