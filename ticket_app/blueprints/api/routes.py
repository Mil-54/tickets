from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from ticket_app.models import Ticket

api_bp = Blueprint('api', __name__)

@api_bp.route('/api/stats')
@login_required
def api_stats():
    if current_user.is_agente():
        base = Ticket.query
    else:
        base = Ticket.query.filter_by(created_by=current_user.id)

    return jsonify({
        'total': base.count(),
        'abiertos': base.filter_by(estado='abierto').count(),
        'en_progreso': base.filter_by(estado='en_progreso').count(),
        'resueltos': base.filter_by(estado='resuelto').count(),
        'cerrados': base.filter_by(estado='cerrado').count(),
    })
