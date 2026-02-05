from app import create_app, db
from app.models.user import User
from app.models.core import Project, Visit, Task, ProjectNode, ProjectDocument, FormTemplate, FormField, FormSubmission
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():
    print("Creating database tables...")
    db.drop_all()
    db.create_all()

    # Create Default Users
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', email='admin@vanti.com', role='admin', full_name='Administrador del Sistema')
        admin.set_password('password')
        db.session.add(admin)
    
    if not User.query.filter_by(username='comercial').first():
        comm = User(username='comercial', email='comercial@vanti.com', role='commercial', full_name='Andrés Comercial')
        comm.set_password('password')
        db.session.add(comm)

    if not User.query.filter_by(username='cartografo').first():
        cart = User(username='cartografo', email='cartografo@vanti.com', role='cartography', full_name='Carlos Cartógrafo')
        cart.set_password('password')
        db.session.add(cart)

    if not User.query.filter_by(username='ingeniero').first():
        eng = User(username='ingeniero', email='ingeniero@vanti.com', role='project_engineer', full_name='Pedro Ingeniero')
        eng.set_password('password')
        db.session.add(eng)

    if not User.query.filter_by(username='analista').first():
        ana = User(username='analista', email='analista@vanti.com', role='analyst', full_name='Ana Analista')
        ana.set_password('password')
        db.session.add(ana)

    if not User.query.filter_by(username='gerente').first():
        ger = User(username='gerente', email='gerente@vanti.com', role='manager', full_name='Gustavo Gerente')
        ger.set_password('password')
        db.session.add(ger)

    if not User.query.filter_by(username='ejecutivo').first():
        exec_user = User(username='ejecutivo', email='ejecutivo@vanti.com', role='ejecutivo', full_name='Elena Ejecutiva')
        exec_user.set_password('password')
        db.session.add(exec_user)

    db.session.commit()
    print("Database initialized with default users.")
