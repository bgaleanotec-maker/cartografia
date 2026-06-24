from datetime import datetime
from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


# ─── Catálogo de roles ─────────────────────────────────────────────────────────
ROLES = {
    'superadmin':  {'label': 'Super Administrador', 'color': 'red',    'icon': 'fa-crown'},
    'admin':       {'label': 'Administrador',        'color': 'purple', 'icon': 'fa-user-shield'},
    'commercial':  {'label': 'Comercial',            'color': 'blue',   'icon': 'fa-handshake'},
    'cartography': {'label': 'Cartografía',          'color': 'green',  'icon': 'fa-map'},
    'analyst':     {'label': 'Analista',             'color': 'cyan',   'icon': 'fa-chart-bar'},
    'manager':     {'label': 'Gerente',              'color': 'orange', 'icon': 'fa-user-tie'},
    'executive':   {'label': 'Ejecutivo',            'color': 'pink',   'icon': 'fa-chart-line'},
}


class User(UserMixin, db.Model):
    __tablename__ = 'user'

    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(64),  unique=True, index=True, nullable=False)
    email         = db.Column(db.String(120), unique=True, index=True, nullable=True)
    full_name     = db.Column(db.String(120), nullable=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role          = db.Column(db.String(20),  nullable=False, default='commercial')

    # SuperAdmin: root, no puede ser eliminado ni degradado desde la UI
    is_superadmin = db.Column(db.Boolean, default=False, nullable=False)

    # Estado de cuenta
    is_active     = db.Column(db.Boolean, default=True, nullable=False)

    # Auditoría
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    last_login    = db.Column(db.DateTime, nullable=True)

    # API key para integración con otros proyectos
    api_key       = db.Column(db.String(64), unique=True, nullable=True, index=True)

    # Relationships
    notifications = db.relationship(
        'Notification', back_populates='user',
        foreign_keys='Notification.user_id',
        lazy='dynamic', cascade='all, delete-orphan'
    )

    # ── Auth ──────────────────────────────────────────────────────────────────
    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return str(self.id)

    # ── Roles ─────────────────────────────────────────────────────────────────
    @property
    def role_label(self) -> str:
        return ROLES.get(self.role, {}).get('label', self.role.title())

    @property
    def role_color(self) -> str:
        return ROLES.get(self.role, {}).get('color', 'gray')

    @property
    def role_icon(self) -> str:
        return ROLES.get(self.role, {}).get('icon', 'fa-user')

    def has_role(self, *roles) -> bool:
        if self.is_superadmin:
            return True
        return self.role in roles

    def can_access_admin(self) -> bool:
        return self.is_superadmin or self.role in ('admin', 'superadmin')

    # ── Notificaciones ────────────────────────────────────────────────────────
    @property
    def unread_count(self) -> int:
        return self.notifications.filter_by(read=False).count()

    def __repr__(self):
        flag = ' [SA]' if self.is_superadmin else ''
        return f'<User {self.username} ({self.role}){flag}>'
