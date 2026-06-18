import random
from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from ticket_app import db
from ticket_app.models import User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            if not user.is_active:
                flash('Tu cuenta está desactivada. Contacta al administrador.', 'error')
                return redirect(url_for('auth.login'))
            login_user(user, remember=True)
            next_page = request.args.get('next')
            # Security check for open redirect vulnerability
            if next_page and not next_page.startswith('/'):
                next_page = None
            return redirect(next_page or url_for('main.dashboard'))
        flash('Correo o contraseña incorrectos.', 'error')

    return render_template('login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        password2 = request.form.get('password2', '')
        role = request.form.get('role', 'cliente')

        if not username or not email or not password:
            flash('Todos los campos son obligatorios.', 'error')
        elif password != password2:
            flash('Las contraseñas no coinciden.', 'error')
        elif len(password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres.', 'error')
        elif User.query.filter_by(email=email).first():
            flash('Ya existe una cuenta con ese correo.', 'error')
        elif User.query.filter_by(username=username).first():
            flash('Ese nombre de usuario ya está en uso.', 'error')
        elif role not in ('agente', 'cliente'):
            flash('Rol inválido.', 'error')
        else:
            colores_avatar = current_app.config.get('COLORES_AVATAR', ['#7C3AED'])
            user = User(
                username=username,
                email=email,
                role=role,
                avatar_color=random.choice(colores_avatar)
            )
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user, remember=True)
            flash(f'¡Bienvenido, {username}!', 'success')
            return redirect(url_for('main.dashboard'))

    return render_template('register.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión correctamente.', 'info')
    return redirect(url_for('auth.login'))
