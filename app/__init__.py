from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_cors import CORS
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
        return User.query.get(int(user_id))

    # Error handler to show actual errors (debug in production temporarily)
    @app.errorhandler(500)
    def internal_error(error):
        import traceback
        tb = traceback.format_exc()
        return f"""<html><body style="background:#0f172a;color:#f8fafc;font-family:monospace;padding:20px">
        <h1 style="color:#ef4444">Error 500</h1>
        <pre style="background:#1e293b;padding:15px;border-radius:8px;overflow:auto;color:#fbbf24">{tb}</pre>
        <p style="color:#94a3b8">Error: {error}</p>
        <a href="/login" style="color:#3b82f6">Volver al login</a>
        </body></html>""", 500

    return app
