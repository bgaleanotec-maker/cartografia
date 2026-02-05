from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user
from app.models.user import User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        # Temporary simple login for prototype
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user is None or not user.check_password(password):
            flash('Invalid username or password')
            return redirect(url_for('auth.login'))
            
        login_user(user)
        return redirect(url_for('main.index'))
        
    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.index'))
