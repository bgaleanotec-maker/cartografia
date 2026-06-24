"""
seed_users.py — Inicialización de usuarios del sistema
=======================================================
Ejecutar UNA VEZ después de init_db.py para crear todos los usuarios base.

Uso:
    python seed_users.py
"""
import sys
import os
import secrets

sys.path.append(os.getcwd())

from app import create_app, db
from app.models.user import User
from app.models.notification import Notification

app = create_app()


def seed_users():
    with app.app_context():

        # ── SUPER ADMIN ─────────────────────────────────────────────────────
        # bgaleanotec — acceso total, root del sistema
        sa = User.query.filter_by(username='bgaleanotec').first()
        if not sa:
            sa = User(
                username     = 'bgaleanotec',
                email        = 'bgaleanotec@gmail.com',
                full_name    = 'Brian Galeano',
                role         = 'superadmin',
                is_superadmin= True,
                is_active    = True,
                api_key      = secrets.token_hex(24),
            )
            sa.set_password('Vanti2026*')
            db.session.add(sa)
            print("✅  SuperAdmin 'bgaleanotec' creado.")
        else:
            # Aseguramos que tenga el flag aunque ya existía
            sa.is_superadmin = True
            sa.role          = 'superadmin'
            if not sa.api_key:
                sa.api_key = secrets.token_hex(24)
            print("ℹ️   SuperAdmin 'bgaleanotec' ya existe — flags actualizados.")

        # ── USUARIOS BASE ────────────────────────────────────────────────────
        base_users = [
            # username        email                           full_name           password      role
            ('admin',         'admin@vanti.com',              'Administrador',    'Vanti2026*', 'admin'),
            ('comercial',     'comercial@vanti.com',          'Agente Comercial', 'password',   'commercial'),
            ('cartografo',    'cartografo@vanti.com',         'Cartógrafo',       'password',   'cartography'),
            ('analista',      'analista@vanti.com',           'Analista GIS',     'password',   'analyst'),
            ('gerente',       'gerente@vanti.com',            'Gerente',          'password',   'manager'),
            ('ejecutivo',     'ejecutivo@vanti.com',          'Ejecutivo',        'password',   'executive'),
        ]

        for username, email, full_name, password, role in base_users:
            existing = User.query.filter_by(username=username).first()
            if not existing:
                user = User(
                    username  = username,
                    email     = email,
                    full_name = full_name,
                    role      = role,
                    is_active = True,
                    api_key   = secrets.token_hex(24),
                )
                user.set_password(password)
                db.session.add(user)
                print(f"✅  Usuario '{username}' ({role}) creado.")
            else:
                if not existing.api_key:
                    existing.api_key = secrets.token_hex(24)
                print(f"ℹ️   Usuario '{username}' ya existe.")

        db.session.commit()

        # ── NOTIFICACIÓN DE BIENVENIDA ───────────────────────────────────────
        bgale = User.query.filter_by(username='bgaleanotec').first()
        if bgale and bgale.notifications.count() == 0:
            welcome = Notification(
                user_id        = bgale.id,
                title          = '🎉 Bienvenido al Gestor Cartográfico',
                message        = ('Sistema listo. Usuarios base creados. '
                                  'Visita /superadmin para gestionar usuarios y notificaciones.'),
                notif_type     = 'success',
                source_project = 'gestor-cartografico',
                link           = '/superadmin',
                created_by_id  = bgale.id,
            )
            db.session.add(welcome)
            db.session.commit()
            print("✅  Notificación de bienvenida creada para bgaleanotec.")

        # ── RESUMEN ──────────────────────────────────────────────────────────
        total = User.query.count()
        print(f"\n{'─'*50}")
        print(f"  Total usuarios en BD: {total}")
        print(f"  SuperAdmin:           bgaleanotec / Vanti2026*")
        print(f"  Admin:                admin        / Vanti2026*")
        print(f"  Otros (demo):         password")
        print(f"{'─'*50}")

        # Mostrar API keys
        print("\n  API Keys (guardar en un lugar seguro):")
        for u in User.query.all():
            print(f"  [{u.role:12s}] {u.username:20s} → {u.api_key or 'sin key'}")


if __name__ == '__main__':
    seed_users()
