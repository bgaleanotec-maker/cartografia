import os
import secrets
from app import create_app, db
from app.models.user import User
from app.models.core import Project, Visit, Task
from app.models.notification import Notification
from app.models.workflow import WorkflowTask
from app.models.core import ProjectNode
from app.models.tracking import ProcessRequest, TeamAssignment, ExecutiveFieldConfig

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User}

def init_database():
    """Crea tablas y usuarios base si no existen."""
    with app.app_context():
        db.create_all()

        # Agregar columnas nuevas a tablas existentes (PostgreSQL no las agrega con create_all)
        # Usa engine.connect() para DDL — cada columna es su propia transacción,
        # evitando que un fallo deje la sesión en estado abortado.
        from sqlalchemy import text, inspect
        inspector = inspect(db.engine)

        # Columnas nuevas de Project para backlog
        existing_cols = [c['name'] for c in inspector.get_columns('project')]
        new_cols = {
            'department': 'VARCHAR(100)',
            'municipality': 'VARCHAR(100)',
            'potential_clients': 'INTEGER DEFAULT 0',
            'estimated_meters': 'FLOAT DEFAULT 0',
            'start_lat': 'FLOAT',
            'start_lng': 'FLOAT',
            'end_lat': 'FLOAT',
            'end_lng': 'FLOAT',
            'cluster_id': 'VARCHAR(50)',
            'cluster_name': 'VARCHAR(100)',
            'priority': 'INTEGER DEFAULT 3',
            'backlog_notes': 'TEXT',
            # Tabla maestra SGI
            'tracking_id': 'VARCHAR(32)',
            'base_address': 'VARCHAR(256)',
            'malla': 'VARCHAR(64)',
            'relevancia': 'VARCHAR(64)',
            'stage': "VARCHAR(64)",
            'assigned_date': 'TIMESTAMP',
            'visit_date': 'TIMESTAMP',
            'support_notes': 'TEXT',
            'pdi_notes': 'TEXT',
            'total_value': 'FLOAT DEFAULT 0',
            'value_per_client': 'FLOAT DEFAULT 0',
            'manager_status': "VARCHAR(32) DEFAULT 'pending_approval'",
            'manager_observations': 'TEXT',
            'cartographer_user_id': 'INTEGER',
            'mask_request_sent_at': 'TIMESTAMP',
            'mask_number': 'VARCHAR(64)',
            'mask_received_at': 'TIMESTAMP',
            'sap_budget_date': 'TIMESTAMP',
        }
        with db.engine.connect() as conn:
            for col_name, col_type in new_cols.items():
                if col_name not in existing_cols:
                    try:
                        conn.execute(text(f'ALTER TABLE project ADD COLUMN {col_name} {col_type}'))
                        conn.commit()
                        print(f"  + Columna '{col_name}' agregada a project")
                    except Exception as e:
                        conn.rollback()
                        print(f"  ~ Columna '{col_name}': {e}")

        # Columnas nuevas de ProjectNode (censo corto/largo plazo + terreno)
        node_cols = {
            'potential_clients_short': 'INTEGER DEFAULT 0',
            'potential_clients_long': 'INTEGER DEFAULT 0',
            'terrain_conditions': 'TEXT',
        }
        existing_node_cols = [c['name'] for c in inspector.get_columns('project_node')]
        with db.engine.connect() as conn:
            for col_name, col_type in node_cols.items():
                if col_name not in existing_node_cols:
                    try:
                        conn.execute(text(f'ALTER TABLE project_node ADD COLUMN {col_name} {col_type}'))
                        conn.commit()
                        print(f"  + Columna '{col_name}' agregada a project_node")
                    except Exception as e:
                        conn.rollback()
                        print(f"  ~ Columna '{col_name}': {e}")

        # Solo seed si no hay usuarios
        if User.query.first() is None:
            print("Inicializando usuarios base...")

            sa = User(
                username='bgaleanotec',
                email='bgaleanotec@gmail.com',
                full_name='Brian Galeano',
                role='superadmin',
                is_superadmin=True,
                is_active=True,
                api_key=secrets.token_hex(24),
            )
            sa.set_password('Vanti2026*')
            db.session.add(sa)

            base_users = [
                ('admin', 'admin@vanti.com', 'Administrador', 'Vanti2026*', 'admin'),
                ('comercial', 'comercial@vanti.com', 'Agente Comercial', 'password', 'commercial'),
                ('cartografo', 'cartografo@vanti.com', 'Cartógrafo', 'password', 'cartography'),
                ('analista', 'analista@vanti.com', 'Analista GIS', 'password', 'analyst'),
                ('gerente', 'gerente@vanti.com', 'Gerente', 'password', 'manager'),
                ('ejecutivo', 'ejecutivo@vanti.com', 'Ejecutivo', 'password', 'executive'),
            ]

            for username, email, full_name, password, role in base_users:
                user = User(
                    username=username,
                    email=email,
                    full_name=full_name,
                    role=role,
                    is_active=True,
                    api_key=secrets.token_hex(24),
                )
                user.set_password(password)
                db.session.add(user)

            db.session.commit()
            print("Usuarios base creados exitosamente.")
        else:
            print("Base de datos ya inicializada.")

        # Seed de ejecutivos comerciales reales (idempotente)
        real_executives = [
            ('aida.suarez',   'Aida Suárez'),
            ('daniel.amaya',  'Daniel Amaya'),
            ('vanesa.lamprea','Vanesa Lamprea'),
        ]
        seeded = False
        for username, full_name in real_executives:
            exists = User.query.filter(
                (User.username == username) | (User.full_name == full_name)
            ).first()
            if not exists:
                u = User(username=username,
                         email=f'{username}@vanti.com',
                         full_name=full_name,
                         role='commercial',
                         is_active=True,
                         api_key=secrets.token_hex(24))
                u.set_password('Vanti2026*')
                db.session.add(u)
                seeded = True
                print(f"  + Ejecutivo comercial '{full_name}' creado")
        if seeded:
            db.session.commit()

# Auto-inicializar al arrancar (no bloquear si falla)
try:
    init_database()
except Exception as e:
    print(f"ADVERTENCIA: No se pudo inicializar la BD: {e}")
    print("La app seguirá funcionando, inicializar BD manualmente.")

if __name__ == '__main__':
    app.run(debug=True)
