from flask import Blueprint, request, jsonify
from app import db
from app.models.core import Project, Visit, ProjectNode, ProjectDocument
from app.models.user import User
from flask_login import current_user
import json
import os
from werkzeug.utils import secure_filename
from datetime import datetime

from app.services.document_service import document_service

api_bp = Blueprint('api', __name__)


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
    if 'gas_points' in data: node.gas_points = int(data.get('gas_points') or 0)
    if 'manual_length' in data: node.manual_length = float(data.get('manual_length') or 0.0)
    
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
        file_path = os.path.join(UPLOAD_FOLDER, unique_name)
        file.save(file_path)
        
        node.photo_url = unique_name
        db.session.commit()
        
        return jsonify({'status': 'success', 'photo_url': unique_name}), 201
