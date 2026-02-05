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
    
    from app.models.user import User
    from app.models.core import Project, Visit, Task

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    return app
