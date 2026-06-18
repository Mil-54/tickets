from flask import Blueprint, render_template, redirect, url_for, current_app
from flask_login import login_required, current_user
from ticket_app.models import User, Ticket

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))


@main_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_agente():
        tickets_base = Ticket.query
    else:
        tickets_base = Ticket.query.filter_by(created_by=current_user.id)

    total = tickets_base.count()
    abiertos = tickets_base.filter_by(estado='abierto').count()
    en_progreso = tickets_base.filter_by(estado='en_progreso').count()
    resueltos = tickets_base.filter_by(estado='resuelto').count()
    cerrados = tickets_base.filter_by(estado='cerrado').count()

    recientes = tickets_base.order_by(Ticket.created_at.desc()).limit(8).all()

    # Estadísticas por categoría para agentes
    cat_stats = []
    if current_user.is_agente():
        categorias = current_app.config.get('CATEGORIAS', [])
        for cat in categorias:
            count = Ticket.query.filter_by(categoria=cat).count()
            if count > 0:
                cat_stats.append({'nombre': cat, 'total': count})

    # Agentes disponibles
    agentes = User.query.filter_by(role='agente', is_active=True).all() if current_user.is_agente() else []

    return render_template(
        'dashboard.html',
        total=total,
        abiertos=abiertos,
        en_progreso=en_progreso,
        resueltos=resueltos,
        cerrados=cerrados,
        recientes=recientes,
        cat_stats=cat_stats,
        agentes=agentes,
    )
