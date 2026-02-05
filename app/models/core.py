from datetime import datetime
from app import db


class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(32), default='prospecting') 
    address = db.Column(db.String(256))
    
    display_name = "Zona / Vereda" # Alias for Project Name in UI

    # Workflow Phases
    # 'prospecting', 'cartography', 'viability', 'approval', 'execution', 'finished'
    phase = db.Column(db.String(32), default='prospecting')

    # CRM & Escalation Fields
    project_type = db.Column(db.String(50), default='expansion') # expansion, connexion, maintenance
    estimated_cost = db.Column(db.Float, default=0.0)
    manager_approval_status = db.Column(db.String(20), default='not_required') # pending, approved, rejected
    manager_comment = db.Column(db.Text)

    
    # Phase Timestamps
    cartography_start_at = db.Column(db.DateTime)
    viability_start_at = db.Column(db.DateTime)
    approval_start_at = db.Column(db.DateTime)
    execution_start_at = db.Column(db.DateTime)
    finished_at = db.Column(db.DateTime)

    # SLA / Viability
    # 'green' (on time), 'yellow' (warning), 'red' (overdue/critical)
    sla_status = db.Column(db.String(16), default='green') 
    viability_status = db.Column(db.String(32), default='pending') # pending, viable, non_viable
    
    # Execution / Construction
    execution_progress = db.Column(db.Integer, default=0)
    execution_status = db.Column(db.String(32), default='not_started') # not_started, in_progress, completed
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    commercial_user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    commercial = db.relationship('User', foreign_keys=[commercial_user_id])
    
    # Relationships
    nodes = db.relationship('ProjectNode', back_populates='project', lazy=True)
    visits = db.relationship('Visit', back_populates='project', lazy=True)
    documents = db.relationship('ProjectDocument', back_populates='project', lazy=True)

class Visit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    local_id = db.Column(db.String(128))
    notes = db.Column(db.Text)
    census_data = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Optional: link to user if logged in
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_by = db.relationship('User', foreign_keys=[created_by_id])

    project = db.relationship('Project', back_populates='visits')

    def to_dict(self):
        return {
            'id': self.id,
            'local_id': self.local_id,
            'project_id': self.project_id,
            'notes': self.notes,
            'census_data': self.census_data,
            'created_at': self.created_at.isoformat()
        }

class ProjectDocument(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    filename = db.Column(db.String(256), nullable=False)
    file_type = db.Column(db.String(32)) # pdf, jpg, docx
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    project = db.relationship('Project', back_populates='documents')
    
    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'file_type': self.file_type,
            'uploaded_at': self.uploaded_at.isoformat()
        }


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(256))
    status = db.Column(db.String(32), default='pending')
    due_date = db.Column(db.DateTime)
    
    assigned_role = db.Column(db.String(32)) # 'cartography', 'projects'


class ProjectNode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    sequence = db.Column(db.Integer, nullable=False)
    manual_length = db.Column(db.Float, default=0.0)
    
    # New metrics per node
    potential_clients = db.Column(db.Integer, default=0)
    gas_points = db.Column(db.Integer, default=0)
    
    # Advanced Attributes
    has_water_source = db.Column(db.Boolean, default=False)
    is_rocky_ground = db.Column(db.Boolean, default=False)
    observations = db.Column(db.Text)
    photo_url = db.Column(db.String(256)) # Path to uploaded evidence
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    project = db.relationship('Project', back_populates='nodes')

    def to_dict(self):
        return {
            'id': self.id,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'sequence': self.sequence,
            'manual_length': self.manual_length,
            'manual_length': self.manual_length,
            'potential_clients': self.potential_clients,
            'gas_points': self.gas_points,
            'has_water_source': self.has_water_source,
            'is_rocky_ground': self.is_rocky_ground,
            'observations': self.observations,
            'photo_url': self.photo_url
        }

# Dynamic CRM Models
class FormTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text)
    hook = db.Column(db.String(64)) # e.g., 'on_viability', 'on_construction'
    role_access = db.Column(db.String(64)) # e.g., 'cartography', 'project_engineer'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    fields = db.relationship('FormField', backref='template', lazy=True, order_by='FormField.sequence')

class FormField(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, db.ForeignKey('form_template.id'), nullable=False)
    label = db.Column(db.String(256), nullable=False)
    field_type = db.Column(db.String(32), nullable=False) # text, number, boolean, file, select
    options = db.Column(db.Text) # JSON string for select options
    required = db.Column(db.Boolean, default=False)
    sequence = db.Column(db.Integer, default=0)

class FormSubmission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    form_template_id = db.Column(db.Integer, db.ForeignKey('form_template.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    data = db.Column(db.Text) # JSON string storing {field_id: value}
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    template = db.relationship('FormTemplate')
    user = db.relationship('User')
    project = db.relationship('Project', backref=db.backref('form_submissions', lazy=True))

