import sys
import os
sys.path.append(os.getcwd())

from app import create_app, db
from app.models.user import User

app = create_app()

def seed_users():
    with app.app_context():
        # Create users if they don't exist
        users = [
            {'username': 'admin', 'password': 'password', 'role': 'admin'},
            {'username': 'comercial', 'password': 'password', 'role': 'commercial'},
            {'username': 'cartografo', 'password': 'password', 'role': 'cartography'},
            {'username': 'ingeniero', 'password': 'password', 'role': 'projects'},
            {'username': 'ejecutivo', 'password': 'password', 'role': 'executive'},
            {'username': 'gerente', 'password': 'password', 'role': 'manager'}
        ]

        for u in users:
            existing = User.query.filter_by(username=u['username']).first()
            if not existing:
                print(f"Creating user: {u['username']}")
                user = User(username=u['username'], role=u['role'])
                user.set_password(u['password'])
                db.session.add(user)
            else:
                print(f"User {u['username']} already exists.")
        
        db.session.commit()
        print("Users seeded successfully.")

if __name__ == '__main__':
    seed_users()
