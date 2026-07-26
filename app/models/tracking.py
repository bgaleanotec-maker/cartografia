"""
tracking.py — Tabla maestra "Gestion - Apoyo Cartografia" (SGI)
================================================================
Modela el Excel clave del area:
  - ProcessRequest  : las 3 solicitudes SGI por proyecto (Cartografia, Diseno,
                      Informe Tecnico) con ANS individual, fechas y semaforo.
  - TeamAssignment  : relacion ejecutivo <-> cartografo (M:N) con soporte de
                      reasignacion / vacaciones / temporadas.
  - ExecutiveFieldConfig : que columnas son visibles/obligatorias por ejecutivo.

Tambien define el catalogo de campos (FIELD_CATALOG), las opciones de estado de
terreno (TERRAIN_OPTIONS) y las etapas (STAGE_OPTIONS).
"""
import json
from datetime import datetime, timedelta
from app import db


# ── Catalogos / opciones ────────────────────────────────────────────────────

STAGE_OPTIONS = [
    '0. Definición alcance',
    '1. Cartografía',
    '2. Diseño',
    '3. Informe Técnico',
    '4. Liberación presupuesto',
    '5. Gerencia',
    '6. Ejecución',
    '7. Finalizado',
]

ESTADO_OPTIONS = ['PENDIENTE', 'ABIERTO', 'CERRADO']
ANS_OPTIONS = ['DENTRO DE PLAZO', 'FUERA DE PLAZO', 'PENDIENTE']

# Estado de terreno (multi-select / checkboxes)
TERRAIN_OPTIONS = [
    {'key': 'normal',              'label': 'Normal'},
    {'key': 'inundacion_alta',     'label': 'Zona Riesgo Inundación Alta'},
    {'key': 'inundacion_media',    'label': 'Zona Riesgo Inundación Media'},
    {'key': 'inundacion_baja',     'label': 'Zona Riesgo Inundación Baja'},
    {'key': 'proteccion_ambiental','label': 'Zona de Protección Ambiental'},
    {'key': 'ronda_hidraulica',    'label': 'Ronda Hidráulica'},
    {'key': 'remocion_alta',       'label': 'Zona Remoción Alta'},
    {'key': 'remocion_media',      'label': 'Zona Remoción Media'},
    {'key': 'remocion_baja',       'label': 'Zona Remoción Baja'},
    {'key': 'servidumbre',         'label': 'Servidumbre'},
]

# Tipos de proceso SGI (en cadena, no simultaneos). ANS individual por cada uno.
PROCESS_TYPES = [
    {'key': 'cartografia',     'label': 'Gestión Cartográfica', 'ans_days': 15},
    {'key': 'diseno',          'label': 'Diseño de Redes',      'ans_days': 15},
    {'key': 'informe_tecnico', 'label': 'Informe Técnico',      'ans_days': 18},
]

MANAGER_STATUS_OPTIONS = [
    {'key': 'pending_approval', 'label': 'Pendiente aprobación', 'color': 'yellow'},
    {'key': 'approved',         'label': 'Aprobado',             'color': 'green'},
    {'key': 'rejected',         'label': 'Rechazado',            'color': 'red'},
    {'key': 'returned',         'label': 'Devuelto a revisión',  'color': 'orange'},
]

# Catalogo canonico de campos de la tabla maestra (para config por ejecutivo).
# group: agrupacion de cabecera | type: text/number/date/select/textarea
FIELD_CATALOG = [
    # General (Gestion Apoyo)
    {'key': 'tracking_id',   'label': 'ID Seguimiento',          'group': 'General', 'type': 'text'},
    {'key': 'municipality',  'label': 'Municipio',               'group': 'General', 'type': 'text'},
    {'key': 'commercial',    'label': 'Ejecutivo Comercial',     'group': 'General', 'type': 'select'},
    {'key': 'cartographer',  'label': 'Cartógrafo',              'group': 'General', 'type': 'select'},
    {'key': 'relevancia',    'label': 'Relevancia',              'group': 'General', 'type': 'text'},
    {'key': 'name',          'label': 'Proyecto',                'group': 'General', 'type': 'text'},
    {'key': 'base_address',  'label': 'Dirección Base',          'group': 'General', 'type': 'text'},
    {'key': 'malla',         'label': 'Malla',                   'group': 'General', 'type': 'text'},
    {'key': 'stage',         'label': 'Estado',                  'group': 'General', 'type': 'select', 'options': STAGE_OPTIONS},
    {'key': 'potential_clients', 'label': 'Potencial SH',        'group': 'General', 'type': 'number'},
    {'key': 'assigned_date', 'label': 'Fecha asignación',        'group': 'General', 'type': 'date'},
    {'key': 'visit_date',    'label': 'Fecha ejecución visita',  'group': 'General', 'type': 'date'},
    {'key': 'support_notes', 'label': 'Observaciones Apoyo Cartografía', 'group': 'General', 'type': 'textarea'},
    # Gestion Cartografica
    {'key': 'cartografia.numero_solicitud', 'label': 'N° Solicitud',  'group': 'Gestión Cartográfica', 'type': 'text'},
    {'key': 'cartografia.fecha_solicitud',  'label': 'Fecha solicitud','group': 'Gestión Cartográfica', 'type': 'date'},
    {'key': 'cartografia.fecha_respuesta',  'label': 'Fecha respuesta','group': 'Gestión Cartográfica', 'type': 'date'},
    {'key': 'cartografia.estado',           'label': 'ESTADO',         'group': 'Gestión Cartográfica', 'type': 'select', 'options': ESTADO_OPTIONS},
    # Diseno de Redes
    {'key': 'diseno.numero_diseno',     'label': 'N° Diseño',      'group': 'Diseño de Redes', 'type': 'text'},
    {'key': 'diseno.numero_solicitud',  'label': 'N° Solicitud',   'group': 'Diseño de Redes', 'type': 'text'},
    {'key': 'diseno.fecha_solicitud',   'label': 'Fecha solicitud','group': 'Diseño de Redes', 'type': 'date'},
    {'key': 'diseno.fecha_respuesta',   'label': 'Fecha respuesta','group': 'Diseño de Redes', 'type': 'date'},
    {'key': 'diseno.estado',            'label': 'ESTADO',         'group': 'Diseño de Redes', 'type': 'select', 'options': ESTADO_OPTIONS},
    # Informe Tecnico
    {'key': 'informe_tecnico.numero_solicitud',      'label': 'N° Solicitud',           'group': 'Informe Técnico', 'type': 'text'},
    {'key': 'informe_tecnico.fecha_solicitud',       'label': 'Fecha solicitud',        'group': 'Informe Técnico', 'type': 'date'},
    {'key': 'informe_tecnico.requiere_visita',       'label': 'Requiere visita',        'group': 'Informe Técnico', 'type': 'select', 'options': ['SI', 'NO']},
    {'key': 'informe_tecnico.fecha_visita_cotizacion','label': 'Fecha visita cotización','group': 'Informe Técnico', 'type': 'date'},
    {'key': 'informe_tecnico.fecha_respuesta',       'label': 'Fecha respuesta',        'group': 'Informe Técnico', 'type': 'date'},
    {'key': 'informe_tecnico.estado',                'label': 'ESTADO',                 'group': 'Informe Técnico', 'type': 'select', 'options': ESTADO_OPTIONS},
    {'key': 'pdi_notes',     'label': 'Observaciones PDI',        'group': 'Informe Técnico', 'type': 'textarea'},
]


# ── Utilidades ANS ──────────────────────────────────────────────────────────

def add_business_days(start_date, days):
    """Suma dias habiles (Lun-Vie) a una fecha."""
    current = start_date
    added = 0
    while added < days:
        current += timedelta(days=1)
        if current.weekday() < 5:
            added += 1
    return current


def business_days_between(start, end):
    """Cuenta dias habiles entre dos fechas (inclusive del rango)."""
    if not start or not end:
        return None
    if end < start:
        return 0
    count = 0
    current = start
    while current < end:
        current += timedelta(days=1)
        if current.weekday() < 5:
            count += 1
    return count


def generate_tracking_id():
    """Genera un ID de seguimiento incremental: SGI-AAAA-NNNN."""
    from app.models.core import Project
    year = datetime.utcnow().year
    prefix = f'SGI-{year}-'
    last = (Project.query
            .filter(Project.tracking_id.like(f'{prefix}%'))
            .order_by(Project.tracking_id.desc())
            .first())
    seq = 1
    if last and last.tracking_id:
        try:
            seq = int(last.tracking_id.split('-')[-1]) + 1
        except (ValueError, IndexError):
            seq = 1
    return f'{prefix}{seq:04d}'


# ── Modelos ─────────────────────────────────────────────────────────────────

class ProcessRequest(db.Model):
    """Una solicitud SGI (Cartografia / Diseno / Informe Tecnico) de un proyecto."""
    __tablename__ = 'process_request'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    process_type = db.Column(db.String(32), nullable=False)  # cartografia|diseno|informe_tecnico

    numero_solicitud = db.Column(db.String(128))     # # solicitud Laserfiche (LF)
    numero_diseno = db.Column(db.String(128))        # solo diseno
    fecha_solicitud = db.Column(db.DateTime)         # arranca el ANS
    fecha_respuesta = db.Column(db.DateTime)
    requiere_visita = db.Column(db.Boolean, default=False)        # solo informe tecnico
    fecha_visita_cotizacion = db.Column(db.DateTime)             # solo informe tecnico

    estado = db.Column(db.String(20), default='PENDIENTE')        # PENDIENTE|ABIERTO|CERRADO
    ans_days = db.Column(db.Integer, default=15)                  # ANS individual
    tiempo_tramite = db.Column(db.Integer)                        # dias habiles solicitud->respuesta
    observaciones = db.Column(db.Text)
    recipient_email = db.Column(db.String(256))                   # Informe Tecnico: destinatario IO cotizacion

    response_file = db.Column(db.String(256))        # formato de respuesta (presupuesto) cargado
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = db.relationship('Project', backref=db.backref('process_requests', lazy='dynamic',
                                                            cascade='all, delete-orphan'))

    # ── Logica ────────────────────────────────────────────────────────────
    @property
    def deadline(self):
        if not self.fecha_solicitud:
            return None
        return add_business_days(self.fecha_solicitud, self.ans_days or 15)

    @property
    def ans_status(self):
        """DENTRO DE PLAZO / FUERA DE PLAZO / PENDIENTE (calculado)."""
        if not self.fecha_solicitud:
            return 'PENDIENTE'
        dl = self.deadline
        ref = self.fecha_respuesta or datetime.utcnow()
        return 'DENTRO DE PLAZO' if ref <= dl else 'FUERA DE PLAZO'

    @property
    def ans_color(self):
        """Semaforo para la UI: green | yellow | red."""
        if not self.fecha_solicitud or self.estado == 'PENDIENTE':
            return 'gray'
        if self.estado == 'CERRADO':
            return 'green' if self.ans_status == 'DENTRO DE PLAZO' else 'red'
        # ABIERTO -> dias restantes
        remaining = (self.deadline - datetime.utcnow()).days
        if remaining < 0:
            return 'red'
        if remaining <= 3:
            return 'yellow'
        return 'green'

    @property
    def is_overdue(self):
        return (self.estado in ('ABIERTO', 'CERRADO')
                and self.fecha_solicitud is not None
                and self.ans_status == 'FUERA DE PLAZO')

    def recompute(self):
        """Recalcula tiempo de tramite (dias habiles) y normaliza estado."""
        if self.fecha_solicitud and self.fecha_respuesta:
            self.tiempo_tramite = business_days_between(self.fecha_solicitud, self.fecha_respuesta)
            if self.estado != 'CERRADO':
                self.estado = 'CERRADO'
        elif self.fecha_solicitud:
            self.tiempo_tramite = business_days_between(self.fecha_solicitud, datetime.utcnow())
            if self.estado == 'PENDIENTE':
                self.estado = 'ABIERTO'
        else:
            self.tiempo_tramite = None

    @property
    def label(self):
        return next((p['label'] for p in PROCESS_TYPES if p['key'] == self.process_type),
                    self.process_type)

    def to_dict(self):
        return {
            'id': self.id,
            'process_type': self.process_type,
            'numero_solicitud': self.numero_solicitud,
            'numero_diseno': self.numero_diseno,
            'fecha_solicitud': self.fecha_solicitud.strftime('%Y-%m-%d') if self.fecha_solicitud else '',
            'fecha_respuesta': self.fecha_respuesta.strftime('%Y-%m-%d') if self.fecha_respuesta else '',
            'requiere_visita': 'SI' if self.requiere_visita else 'NO',
            'fecha_visita_cotizacion': self.fecha_visita_cotizacion.strftime('%Y-%m-%d') if self.fecha_visita_cotizacion else '',
            'estado': self.estado,
            'ans_status': self.ans_status,
            'ans_color': self.ans_color,
            'tiempo_tramite': self.tiempo_tramite,
            'observaciones': self.observaciones,
            'response_file': self.response_file,
        }


class TeamAssignment(db.Model):
    """Relacion ejecutivo <-> cartografo. active=False => vacaciones/reasignado."""
    __tablename__ = 'team_assignment'

    id = db.Column(db.Integer, primary_key=True)
    executive_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    cartographer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    active = db.Column(db.Boolean, default=True)
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime)
    note = db.Column(db.String(256))  # ej. "vacaciones", "reasignacion temporada alta"

    executive = db.relationship('User', foreign_keys=[executive_id])
    cartographer = db.relationship('User', foreign_keys=[cartographer_id])


class ExecutiveFieldConfig(db.Model):
    """Configuracion de campos (visible/obligatorio) por ejecutivo comercial."""
    __tablename__ = 'executive_field_config'

    id = db.Column(db.Integer, primary_key=True)
    commercial_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    field_key = db.Column(db.String(64), nullable=False)
    visible = db.Column(db.Boolean, default=True)
    required = db.Column(db.Boolean, default=False)
    sequence = db.Column(db.Integer, default=0)

    __table_args__ = (db.UniqueConstraint('commercial_user_id', 'field_key',
                                          name='uq_exec_field'),)


class ActivityType(db.Model):
    """Catálogo PARAMETRIZABLE de tipos de actividad (ej. 'Actualizar Laserfiche').
    Lo administra el rol de cartografía / admin."""
    __tablename__ = 'activity_type'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False, unique=True)
    description = db.Column(db.String(256))
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ProjectActivity(db.Model):
    """Bitácora de actividades por proyecto con trazabilidad de tiempos y responsables."""
    __tablename__ = 'project_activity'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)

    name = db.Column(db.String(128), nullable=False)     # denormalizado del tipo o libre
    activity_type_id = db.Column(db.Integer, db.ForeignKey('activity_type.id'), nullable=True)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='pendiente')  # pendiente | en_progreso | cerrada
    notes = db.Column(db.Text)

    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)   # quien la agrega
    performed_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True) # quien la ejecuta

    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # cuando se agrega
    started_at = db.Column(db.DateTime, nullable=True)            # cuando el cartografo la inicia
    closed_at = db.Column(db.DateTime, nullable=True)            # cuando la cierra

    project = db.relationship('Project', backref=db.backref('activities', lazy='dynamic',
                                                            cascade='all, delete-orphan'))
    activity_type = db.relationship('ActivityType')
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    performed_by = db.relationship('User', foreign_keys=[performed_by_id])

    @property
    def duration_minutes(self):
        if self.started_at and self.closed_at:
            return round((self.closed_at - self.started_at).total_seconds() / 60)
        return None

    @property
    def duration_label(self):
        m = self.duration_minutes
        if m is None:
            return '—'
        if m < 60:
            return f'{m} min'
        h, mm = divmod(m, 60)
        return f'{h}h {mm}m'

    @property
    def status_color(self):
        return {'pendiente': 'gray', 'en_progreso': 'yellow', 'cerrada': 'green'}.get(self.status, 'gray')


def get_field_config(commercial_user_id):
    """Devuelve el catalogo de campos fusionado con la config del ejecutivo.
    Si el ejecutivo no tiene config, todos visibles y ninguno obligatorio."""
    overrides = {}
    if commercial_user_id:
        rows = ExecutiveFieldConfig.query.filter_by(commercial_user_id=commercial_user_id).all()
        overrides = {r.field_key: r for r in rows}

    merged = []
    for idx, field in enumerate(FIELD_CATALOG):
        ov = overrides.get(field['key'])
        merged.append({
            **field,
            'visible': ov.visible if ov else True,
            'required': ov.required if ov else False,
            'sequence': ov.sequence if ov else idx,
        })
    merged.sort(key=lambda f: f['sequence'])
    return merged
