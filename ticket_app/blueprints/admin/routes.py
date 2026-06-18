from flask import Blueprint, render_template, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from ticket_app import db
from ticket_app.models import User

admin_bp = Blueprint('admin', __name__)

@admin_bp.before_request
@login_required
def require_agent():
    if not current_user.is_agente():
        abort(403)


@admin_bp.route('/admin/usuarios')
def admin_usuarios():
    usuarios = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin.html', usuarios=usuarios)


@admin_bp.route('/admin/usuarios/<int:user_id>/toggle', methods=['POST'])
def toggle_usuario(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('No puedes desactivar tu propia cuenta.', 'error')
        return redirect(url_for('admin.admin_usuarios'))
    user.is_active = not user.is_active
    db.session.commit()
    estado = 'activado' if user.is_active else 'desactivado'
    flash(f'Usuario {user.username} {estado}.', 'success')
    return redirect(url_for('admin.admin_usuarios'))


@admin_bp.route('/admin/usuarios/<int:user_id>/rol', methods=['POST'])
def cambiar_rol(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('No puedes cambiar tu propio rol.', 'error')
        return redirect(url_for('admin.admin_usuarios'))
    nuevo_rol = 'agente' if user.role == 'cliente' else 'cliente'
    user.role = nuevo_rol
    db.session.commit()
    flash(f'Rol de {user.username} cambiado a {nuevo_rol}.', 'success')
    return redirect(url_for('admin.admin_usuarios'))
