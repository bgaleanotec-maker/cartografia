from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_cors import CORS
from sqlalchemy.exc import OperationalError
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    CORS(app)

    # Register Blueprints
    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.api import api_bp
    from app.routes.commercial import commercial_bp
    from app.routes.cartography import cartography_bp
    from app.routes.projects import projects_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(commercial_bp)
    app.register_blueprint(cartography_bp)
    app.register_blueprint(projects_bp)
    
    from app.routes.admin import admin_bp
    app.register_blueprint(admin_bp)

    from app.routes.executive import executive_bp
    app.register_blueprint(executive_bp)

    from app.routes.forms import forms_bp
    app.register_blueprint(forms_bp)

    from app.routes.analyst import analyst_bp
    app.register_blueprint(analyst_bp)

    from app.routes.manager import manager_bp
    app.register_blueprint(manager_bp)

    from app.routes.mobile import mobile_bp
    app.register_blueprint(mobile_bp)

    from app.routes.docs import docs_bp
    app.register_blueprint(docs_bp)

    from app.routes.superadmin import superadmin_bp
    app.register_blueprint(superadmin_bp)

    from app.routes.workflow import workflow_bp
    app.register_blueprint(workflow_bp)

    from app.routes.backlog import backlog_bp
    app.register_blueprint(backlog_bp)

    from app.routes.tracking import tracking_bp
    app.register_blueprint(tracking_bp)

    from app.models.user import User
    from app.models.core import Project, Visit, Task
    from app.models.notification import Notification
    from app.models.workflow import WorkflowTask
    from app.models.tracking import (ProcessRequest, TeamAssignment, ExecutiveFieldConfig,
                                      ActivityType, ProjectActivity)

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return User.query.get(int(user_id))
        except OperationalError:
            db.session.rollback()
            return None

    def _db_waking_page():
        """Página amable cuando la BD está despertando (cold start de Render).
        Redirige al login (página buena) en 6s y NO se cachea, para no atrapar al
        usuario en un bucle sobre una URL que falló."""
        from flask import Response
        html = """<!doctype html><html lang="es"><head><meta charset="utf-8">
        <meta http-equiv="refresh" content="6; url=/login?_r=1">
        <title>Iniciando servicio…</title></head>
        <body style="background:#0f172a;color:#e2e8f0;font-family:system-ui,Arial,sans-serif;
        display:flex;align-items:center;justify-content:center;height:100vh;margin:0;text-align:center">
        <div>
          <div style="font-size:42px;margin-bottom:10px">⏳</div>
          <h1 style="font-weight:600;font-size:20px;margin:0 0 8px">Iniciando el servicio…</h1>
          <p style="color:#94a3b8;max-width:420px;margin:0 auto 16px;font-size:14px">
            La base de datos está despertando (plan gratuito de Render). Te llevaremos al
            inicio de sesión automáticamente en unos segundos.</p>
          <a href="/login?_r=1" style="display:inline-block;background:#2563eb;color:#fff;
            text-decoration:none;font-size:14px;padding:8px 18px;border-radius:6px">Ir al inicio de sesión</a>
        </div></body></html>"""
        resp = Response(html, status=503)
        resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        resp.headers['Pragma'] = 'no-cache'
        resp.headers['Retry-After'] = '6'
        return resp

    # Fallo de conexión a la BD (cold start / DNS momentáneo): página amable con auto-retry
    @app.errorhandler(OperationalError)
    def handle_db_operational_error(error):
        try:
            db.session.rollback()
        except Exception:
            pass
        return _db_waking_page()

    @app.errorhandler(500)
    def internal_error(error):
        # Si el 500 fue causado por un fallo de conexión a la BD, mostrar página amable
        import traceback
        tb = traceback.format_exc()
        if ('OperationalError' in tb or 'could not translate host name' in tb
                or 'could not connect to server' in tb or 'psycopg2' in tb):
            return _db_waking_page()
        # Otros 500: log en servidor, mensaje genérico al usuario (sin traceback expuesto)
        print(tb)
        return ("""<!doctype html><html lang="es"><head><meta charset="utf-8">
        <title>Error</title></head>
        <body style="background:#0f172a;color:#e2e8f0;font-family:system-ui,Arial,sans-serif;
        display:flex;align-items:center;justify-content:center;height:100vh;margin:0;text-align:center">
        <div><div style="font-size:42px">⚠️</div>
        <h1 style="font-size:20px;font-weight:600">Ocurrió un error inesperado</h1>
        <p style="color:#94a3b8;font-size:14px">Intenta de nuevo. Si continúa, avisa al administrador.</p>
        <a href="/login" style="color:#38bdf8;font-size:14px">Volver al inicio</a></div>
        </body></html>""", 500)

    return app
