import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'

    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI or 'sqlite:///sst.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,   # Verifica la conexión antes de usarla (reconecta si cayó)
        'pool_recycle': 280,     # Recicla conexiones antes del timeout de 300s de Render
    }
    # Solo para PostgreSQL: timeout de conexión + keepalives (reduce fallos de cold start)
    if (os.environ.get('DATABASE_URL') or '').startswith(('postgres://', 'postgresql://')):
        SQLALCHEMY_ENGINE_OPTIONS['connect_args'] = {
            'connect_timeout': 10,
            'keepalives': 1,
            'keepalives_idle': 30,
            'keepalives_interval': 10,
            'keepalives_count': 5,
        }

    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or os.path.join(BASE_DIR, 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload

    # Ensure upload folder exists at startup
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
