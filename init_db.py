"""
init_db.py — Inicialización de la base de datos
================================================
Crea todas las tablas. NO inserta usuarios de prueba.
Ejecutar ANTES de seed_users.py.

Uso:
    python init_db.py
"""
from app import create_app, db
from app.models.user import User
from app.models.core import Project, Visit, Task, ProjectNode, ProjectDocument, FormTemplate, FormField, FormSubmission
from app.models.notification import Notification

app = create_app()

with app.app_context():
    print("Creando tablas en la base de datos...")
    db.create_all()
    print("✅  Tablas creadas correctamente.")
    print("    Ejecuta 'python seed_users.py' para crear el SuperAdmin y usuarios base.")
