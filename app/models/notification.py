"""
Notification Model — Sistema de notificaciones cross-proyecto
=============================================================
Otros sistemas (Doctor, otros) pueden enviar notificaciones vía API REST
usando su api_key. Las notificaciones aparecen en la campana del navbar.
"""
from datetime import datetime
from app import db


# Tipos de notificación
NOTIF_TYPES = ('info', 'success', 'warning', 'error', 'task', 'alert')

# Proyectos fuente registrados (se puede ampliar)
SOURCE_PROJECTS = (
    'gestor-cartografico',
    'doctor',           # sistema médico / doctor
    'admin',            # sistema admin central
    'external',         # genérico
)


class Notification(db.Model):
    __tablename__ = 'notification'

    id             = db.Column(db.Integer, primary_key=True)

    # Destinatario
    user_id        = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)

    # Contenido
    title          = db.Column(db.String(256), nullable=False)
    message        = db.Column(db.Text, nullable=True)
    notif_type     = db.Column(db.String(20),  nullable=False, default='info')   # info|success|warning|error|task|alert
    source_project = db.Column(db.String(64),  nullable=False, default='gestor-cartografico')
    link           = db.Column(db.String(512), nullable=True)   # URL a abrir al hacer clic

    # Estado
    read           = db.Column(db.Boolean, default=False, nullable=False)
    read_at        = db.Column(db.DateTime, nullable=True)

    # Auditoría
    created_at     = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    created_by_id  = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    # Relaciones
    user           = db.relationship('User', back_populates='notifications',
                                     foreign_keys=[user_id])
    created_by     = db.relationship('User', foreign_keys=[created_by_id])

    # ── Helpers ───────────────────────────────────────────────────────────────
    def mark_read(self):
        self.read    = True
        self.read_at = datetime.utcnow()

    @property
    def icon(self) -> str:
        icons = {
            'info':    'fa-info-circle',
            'success': 'fa-check-circle',
            'warning': 'fa-exclamation-triangle',
            'error':   'fa-times-circle',
            'task':    'fa-tasks',
            'alert':   'fa-bell',
        }
        return icons.get(self.notif_type, 'fa-bell')

    @property
    def color_class(self) -> str:
        colors = {
            'info':    'text-blue-400',
            'success': 'text-green-400',
            'warning': 'text-yellow-400',
            'error':   'text-red-400',
            'task':    'text-purple-400',
            'alert':   'text-orange-400',
        }
        return colors.get(self.notif_type, 'text-gray-400')

    @property
    def bg_class(self) -> str:
        bgs = {
            'info':    'bg-blue-900/20 border-blue-900/40',
            'success': 'bg-green-900/20 border-green-900/40',
            'warning': 'bg-yellow-900/20 border-yellow-900/40',
            'error':   'bg-red-900/20 border-red-900/40',
            'task':    'bg-purple-900/20 border-purple-900/40',
            'alert':   'bg-orange-900/20 border-orange-900/40',
        }
        return bgs.get(self.notif_type, 'bg-gray-800/40 border-gray-700')

    def to_dict(self) -> dict:
        return {
            'id':             self.id,
            'title':          self.title,
            'message':        self.message,
            'type':           self.notif_type,
            'source_project': self.source_project,
            'link':           self.link,
            'read':           self.read,
            'icon':           self.icon,
            'color':          self.color_class,
            'created_at':     self.created_at.isoformat(),
        }

    def __repr__(self):
        return f'<Notification [{self.notif_type}] → user_id={self.user_id}: {self.title[:40]}>'
