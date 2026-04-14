import os
import secrets
from app import create_app, db
from app.models.user import User
from app.models.core import Project, Visit, Task
from app.models.notification import Notification
from app.models.workflow import WorkflowTask

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User}

def init_database():
    """Crea tablas y usuarios base si no existen."""
    with app.app_context():
        db.create_all()

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
                ('ingeniero', 'ingeniero@vanti.com', 'Ing. Proyectos', 'password', 'projects'),
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

# Auto-inicializar al arrancar (no bloquear si falla)
try:
    init_database()
except Exception as e:
    print(f"ADVERTENCIA: No se pudo inicializar la BD: {e}")
    print("La app seguirá funcionando, inicializar BD manualmente.")

if __name__ == '__main__':
    app.run(debug=True)
