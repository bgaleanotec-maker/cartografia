"""
workflow.py — Sistema de flujos de trabajo con seguimiento ANS
=================================================================
Modela las actividades de los roles Cartografia, Proyectos y Ejecutivo
con control de tiempos ANS (Acuerdos de Nivel de Servicio), estados,
aprobaciones/rechazos y trazabilidad completa.
"""
from datetime import datetime, timedelta
from app import db


# ── DEFINICION DE FLUJOS POR ROL ────────────────────────────────────────

WORKFLOW_DEFINITIONS = {
    'cartography': {
        'name': 'Flujo Cartografia',
        'steps': [
            {'code': 'CART_A', 'name': 'Visita de reconocimiento inicial',
             'description': 'Recibir por parte del ejecutivo las zonas que se pasaran a prospeccion de proyectos',
             'ans_days': None, 'requires_approval': False},
            {'code': 'CART_B', 'name': 'Validacion disponibilidad y afectaciones ambientales',
             'description': 'Validacion en Signatural y sistemas de georeferenciacion oficiales (Sinupot, Mapas Bogota, etc)',
             'ans_days': None, 'requires_approval': False},
            {'code': 'CART_C', 'name': 'Visita levantamiento y validacion KMZ inicial',
             'description': 'Definicion de KMZ definitivo en las zonas asignadas, reconocimiento de clientes y lotes (censo)',
             'ans_days': None, 'requires_approval': False},
            {'code': 'CART_D', 'name': 'Solicitar actualizacion cartografica',
             'description': 'Elaboracion de insumos para loteo. Se solicita en Laserfiche con detalle de lotes (JPEG o Word)',
             'ans_days': 15, 'requires_approval': False},
            {'code': 'CART_E', 'name': 'Recibir actualizacion cartografica',
             'description': 'Recibir a satisfaccion. Si se rechaza dentro de 3 dias habiles = 8 dias respuesta. Fuera de 3 dias = 15 dias nuevos',
             'ans_days': 15, 'requires_approval': True},
            {'code': 'CART_F', 'name': 'Solicitar diseno de red',
             'description': 'Solicitar en Laserfiche: KMZ del trazado propuesto (JPEG) y diseno de red para conexion de clientes',
             'ans_days': 15, 'requires_approval': False},
            {'code': 'CART_G', 'name': 'Recibir diseno de red',
             'description': 'Recibir a satisfaccion. Si no coincide se rechaza dentro de 3 dias habiles',
             'ans_days': 15, 'requires_approval': True},
            {'code': 'CART_H', 'name': 'Solicitar firma y autorizacion ejecutivo',
             'description': 'Solicitar al ejecutivo comercial firma y autorizacion del diseno de red final y KMZ final para Informe Tecnico',
             'ans_days': None, 'requires_approval': True},
            {'code': 'CART_I', 'name': 'Solicitar Informe Tecnico',
             'description': 'Montar en formulario Forms: diseno de red, coordenadas, potencial, direccion, consumos, metros, mallas, tipo tuberia',
             'ans_days': 18, 'requires_approval': False},
            {'code': 'CART_J', 'name': 'Visita cotizacion transversal',
             'description': 'Recorrido en terreno con Ingeniero de Obra, area ambiental, gestion de permisos. Identificar condiciones tecnicas y censo (KMZ)',
             'ans_days': None, 'requires_approval': False},
            {'code': 'CART_K', 'name': 'Modificaciones post-visita',
             'description': 'Si se requiere modificacion a diseno o actualizacion cartografica, documentar y solicitar (vuelve a paso D o F)',
             'ans_days': None, 'requires_approval': False},
        ]
    },
    'projects': {
        'name': 'Flujo Proyectos',
        'steps': [
            {'code': 'PROY_A', 'name': 'Seguimiento ANS Informes Tecnicos',
             'description': 'Hacer seguimiento al cumplimiento del ANS sobre la entrega de los Informes Tecnicos',
             'ans_days': None, 'requires_approval': False},
            {'code': 'PROY_B', 'name': 'Recepcion y verificacion Informe Tecnico',
             'description': 'Recepcion y verificacion con el ejecutivo comercial (tiempos ejecucion, afectaciones ambientales, metros, ubicacion)',
             'ans_days': None, 'requires_approval': True},
            {'code': 'PROY_C', 'name': 'Evaluacion financiera',
             'description': 'Garantizar entrega de evaluacion financiera por parte del Ejecutivo para presentacion a gerencia',
             'ans_days': None, 'requires_approval': True},
            {'code': 'PROY_D', 'name': 'Orden de construccion',
             'description': 'Con la aprobacion, diligenciar formato de orden de construccion y solicitar firma al equipo comercial',
             'ans_days': None, 'requires_approval': True},
            {'code': 'PROY_E', 'name': 'Verificacion documental',
             'description': 'Verificar diseno actualizado y cantidades de obra vs cotizacion',
             'ans_days': None, 'requires_approval': False},
            {'code': 'PROY_F', 'name': 'Remitir orden de construccion',
             'description': 'Enviar orden firmada por email a Proyectos de Ingenieria. Solicitar consecutivo de mascara',
             'ans_days': None, 'requires_approval': False},
            {'code': 'PROY_G', 'name': 'Recepcion mascara y carga SAP',
             'description': 'Recibir numero de mascara y proceder a cargar presupuesto en SAP',
             'ans_days': None, 'requires_approval': False},
        ]
    },
    'executive': {
        'name': 'Flujo Ejecutivo',
        'steps': [
            {'code': 'EJEC_H', 'name': 'Solicitar liberacion presupuesto',
             'description': 'Solicitar liberacion del presupuesto al responsable del area comercial',
             'ans_days': None, 'requires_approval': True},
            {'code': 'EJEC_I', 'name': 'Recepcion liberacion presupuesto',
             'description': 'Recibir liberacion y reenviar al area de proyectos de ingenieria',
             'ans_days': None, 'requires_approval': False},
            {'code': 'EJEC_J', 'name': 'Seguimiento Kick-Off',
             'description': 'Seguimiento de asignacion a areas: ambiental, predial, construccion',
             'ans_days': None, 'requires_approval': False},
            {'code': 'EJEC_K', 'name': 'Seguimiento ANS actividades',
             'description': 'Seguimiento al cumplimiento del ANS segun cada actividad asignada',
             'ans_days': None, 'requires_approval': False},
            {'code': 'EJEC_L', 'name': 'Cierre tecnico y financiero',
             'description': 'Verificar metros, CAPEX, clientes, m3/cliente, artefactos, % financiacion, % II',
             'ans_days': None, 'requires_approval': True},
        ]
    }
}


class WorkflowTask(db.Model):
    """Tarea de flujo de trabajo con seguimiento ANS."""
    __tablename__ = 'workflow_task'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)

    # Identificacion
    workflow_role = db.Column(db.String(20), nullable=False)  # cartography, projects, executive
    step_code = db.Column(db.String(20), nullable=False)      # CART_A, PROY_B, etc.
    step_name = db.Column(db.String(200), nullable=False)
    step_description = db.Column(db.Text)
    step_order = db.Column(db.Integer, default=0)

    # Estado
    status = db.Column(db.String(20), default='pending')
    # pending | in_progress | waiting_approval | approved | rejected | completed | blocked

    # Asignacion
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    assigned_to = db.relationship('User', foreign_keys=[assigned_to_id])

    # ANS (Acuerdo de Nivel de Servicio)
    ans_days = db.Column(db.Integer, nullable=True)        # Dias habiles de ANS
    ans_deadline = db.Column(db.DateTime, nullable=True)    # Fecha limite calculada
    ans_status = db.Column(db.String(10), default='green')  # green | yellow | red | expired

    # Fechas
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    deadline_at = db.Column(db.DateTime, nullable=True)

    # Aprobacion/Rechazo
    requires_approval = db.Column(db.Boolean, default=False)
    approved_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    approved_by = db.relationship('User', foreign_keys=[approved_by_id])
    approval_date = db.Column(db.DateTime, nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)
    rejection_count = db.Column(db.Integer, default=0)

    # Documentos y notas
    notes = db.Column(db.Text, nullable=True)
    attachments = db.Column(db.Text, nullable=True)  # JSON list of filenames

    # Relacion con proyecto
    project = db.relationship('Project', backref=db.backref('workflow_tasks', lazy='dynamic'))

    def start(self):
        """Iniciar la tarea y calcular deadline ANS."""
        self.status = 'in_progress'
        self.started_at = datetime.utcnow()
        if self.ans_days:
            self.deadline_at = self._add_business_days(datetime.utcnow(), self.ans_days)
            self.ans_deadline = self.deadline_at
        self.update_ans_status()

    def complete(self):
        self.status = 'completed'
        self.completed_at = datetime.utcnow()
        self.update_ans_status()

    def approve(self, user_id):
        self.status = 'approved'
        self.approved_by_id = user_id
        self.approval_date = datetime.utcnow()
        self.completed_at = datetime.utcnow()

    def reject(self, reason, user_id):
        self.status = 'rejected'
        self.rejection_reason = reason
        self.rejection_count += 1
        self.approved_by_id = user_id
        self.approval_date = datetime.utcnow()
        # Recalcular ANS segun reglas de negocio
        if self.step_code in ('CART_E', 'CART_G'):
            if self.rejection_count <= 1 and self._within_business_days(3):
                # Dentro de 3 dias habiles: 8 dias respuesta
                self.deadline_at = self._add_business_days(datetime.utcnow(), 8)
            else:
                # Fuera de 3 dias habiles: 15 dias nuevos
                self.deadline_at = self._add_business_days(datetime.utcnow(), 15)
            self.ans_deadline = self.deadline_at
        self.status = 'in_progress'  # Vuelve a estar en progreso

    def update_ans_status(self):
        """Actualizar semaforo ANS."""
        if not self.deadline_at or self.status in ('completed', 'approved'):
            self.ans_status = 'green'
            return

        now = datetime.utcnow()
        remaining = (self.deadline_at - now).days

        if remaining < 0:
            self.ans_status = 'expired'
        elif remaining <= 3:
            self.ans_status = 'red'
        elif remaining <= 7:
            self.ans_status = 'yellow'
        else:
            self.ans_status = 'green'

    def _add_business_days(self, start_date, days):
        current = start_date
        added = 0
        while added < days:
            current += timedelta(days=1)
            if current.weekday() < 5:  # Lunes-Viernes
                added += 1
        return current

    def _within_business_days(self, days):
        if not self.started_at:
            return True
        deadline = self._add_business_days(self.started_at, days)
        return datetime.utcnow() <= deadline

    @property
    def days_remaining(self):
        if not self.deadline_at:
            return None
        return (self.deadline_at - datetime.utcnow()).days

    @property
    def days_elapsed(self):
        if not self.started_at:
            return 0
        return (datetime.utcnow() - self.started_at).days

    @property
    def is_overdue(self):
        return self.ans_status == 'expired'

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'step_code': self.step_code,
            'step_name': self.step_name,
            'status': self.status,
            'ans_days': self.ans_days,
            'ans_status': self.ans_status,
            'days_remaining': self.days_remaining,
            'days_elapsed': self.days_elapsed,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'deadline_at': self.deadline_at.isoformat() if self.deadline_at else None,
            'rejection_count': self.rejection_count,
            'notes': self.notes,
        }


def create_workflow_for_project(project_id, role, assigned_to_id=None):
    """Crea todas las tareas del flujo para un proyecto y rol."""
    defn = WORKFLOW_DEFINITIONS.get(role)
    if not defn:
        return []

    tasks = []
    for idx, step in enumerate(defn['steps']):
        task = WorkflowTask(
            project_id=project_id,
            workflow_role=role,
            step_code=step['code'],
            step_name=step['name'],
            step_description=step.get('description', ''),
            step_order=idx,
            ans_days=step.get('ans_days'),
            requires_approval=step.get('requires_approval', False),
            assigned_to_id=assigned_to_id,
            status='pending'
        )
        db.session.add(task)
        tasks.append(task)

    db.session.commit()
    return tasks
