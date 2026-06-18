from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, request, flash, abort, current_app
from flask_login import login_required, current_user
from sqlalchemy import or_
from ticket_app import db
from ticket_app.models import User, Ticket, Comment, TicketHistory

tickets_bp = Blueprint('tickets', __name__)

def registrar_historial(ticket_id, accion, anterior=None, nuevo=None):
    h = TicketHistory(
        ticket_id=ticket_id,
        user_id=current_user.id,
        accion=accion,
        valor_anterior=anterior,
        valor_nuevo=nuevo
    )
    db.session.add(h)


@tickets_bp.route('/tickets')
@login_required
def tickets():
    estado_f = request.args.get('estado', '')
    prioridad_f = request.args.get('prioridad', '')
    categoria_f = request.args.get('categoria', '')
    asignado_f = request.args.get('asignado', '')
    busqueda = request.args.get('q', '').strip()

    if current_user.is_agente():
        query = Ticket.query
    else:
        query = Ticket.query.filter_by(created_by=current_user.id)

    if estado_f:
        query = query.filter_by(estado=estado_f)
    if prioridad_f:
        query = query.filter_by(prioridad=prioridad_f)
    if categoria_f:
        query = query.filter_by(categoria=categoria_f)
    if asignado_f and current_user.is_agente():
        if asignado_f == 'yo':
            query = query.filter_by(assigned_to=current_user.id)
        elif asignado_f == 'nadie':
            query = query.filter_by(assigned_to=None)
    if busqueda:
        query = query.filter(
            or_(
                Ticket.titulo.ilike(f'%{busqueda}%'),
                Ticket.descripcion.ilike(f'%{busqueda}%')
            )
        )

    page = request.args.get('page', 1, type=int)
    per_page = 12
    pagination = query.order_by(Ticket.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    agentes = User.query.filter_by(role='agente', is_active=True).all() if current_user.is_agente() else []
    categorias = current_app.config.get('CATEGORIAS', [])

    return render_template(
        'tickets.html',
        tickets=pagination.items,
        pagination=pagination,
        categorias=categorias,
        agentes=agentes,
        filtros={
            'estado': estado_f,
            'prioridad': prioridad_f,
            'categoria': categoria_f,
            'asignado': asignado_f,
            'q': busqueda,
        }
    )


@tickets_bp.route('/tickets/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_ticket():
    categorias = current_app.config.get('CATEGORIAS', [])
    if request.method == 'POST':
        titulo = request.form.get('titulo', '').strip()
        descripcion = request.form.get('descripcion', '').strip()
        categoria = request.form.get('categoria', '')
        prioridad = request.form.get('prioridad', 'media')

        if not titulo or not descripcion or not categoria:
            flash('Todos los campos son obligatorios.', 'error')
        elif categoria not in categorias:
            flash('Categoría inválida.', 'error')
        elif prioridad not in ('baja', 'media', 'alta', 'urgente'):
            flash('Prioridad inválida.', 'error')
        else:
            ticket = Ticket(
                titulo=titulo,
                descripcion=descripcion,
                categoria=categoria,
                prioridad=prioridad,
                created_by=current_user.id
            )
            db.session.add(ticket)
            db.session.flush()
            registrar_historial(ticket.id, 'Ticket creado')
            db.session.commit()
            flash(f'Ticket {ticket.ticket_id} creado exitosamente.', 'success')
            return redirect(url_for('tickets.ticket_detalle', ticket_id=ticket.id))

    return render_template('new_ticket.html', categorias=categorias)


@tickets_bp.route('/tickets/<int:ticket_id>')
@login_required
def ticket_detalle(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)

    # Clientes solo ven sus propios tickets
    if not current_user.is_agente() and ticket.created_by != current_user.id:
        abort(403)

    # Comentarios: clientes no ven notas internas
    if current_user.is_agente():
        comentarios = ticket.comments
    else:
        comentarios = [c for c in ticket.comments if not c.es_interno]

    agentes = User.query.filter_by(role='agente', is_active=True).all() if current_user.is_agente() else []

    return render_template(
        'ticket_detail.html',
        ticket=ticket,
        comentarios=comentarios,
        agentes=agentes,
        historial=ticket.history,
    )


@tickets_bp.route('/tickets/<int:ticket_id>/comentar', methods=['POST'])
@login_required
def comentar_ticket(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)

    if not current_user.is_agente() and ticket.created_by != current_user.id:
        abort(403)

    contenido = request.form.get('contenido', '').strip()
    es_interno = request.form.get('es_interno') == 'on' and current_user.is_agente()

    if not contenido:
        flash('El comentario no puede estar vacío.', 'error')
        return redirect(url_for('tickets.ticket_detalle', ticket_id=ticket_id))

    comment = Comment(
        ticket_id=ticket_id,
        user_id=current_user.id,
        contenido=contenido,
        es_interno=es_interno
    )
    db.session.add(comment)
    registrar_historial(ticket_id, 'Comentario agregado')
    db.session.commit()
    flash('Comentario agregado.', 'success')
    return redirect(url_for('tickets.ticket_detalle', ticket_id=ticket_id))


@tickets_bp.route('/tickets/<int:ticket_id>/actualizar', methods=['POST'])
@login_required
def actualizar_ticket(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)

    # Solo agentes o el creador pueden actualizar
    if not current_user.is_agente() and ticket.created_by != current_user.id:
        abort(403)

    campo = request.form.get('campo')
    valor = request.form.get('valor')

    if campo == 'estado' and current_user.is_agente():
        estados_validos = ('abierto', 'en_progreso', 'resuelto', 'cerrado')
        if valor in estados_validos:
            anterior = ticket.estado
            ticket.estado = valor
            ticket.updated_at = datetime.utcnow()
            if valor == 'resuelto':
                ticket.resolved_at = datetime.utcnow()
            registrar_historial(ticket_id, 'Estado actualizado', anterior, valor)
            db.session.commit()
            flash(f'Estado actualizado a "{ticket.estado_label}".', 'success')

    elif campo == 'prioridad' and current_user.is_agente():
        prioridades_validas = ('baja', 'media', 'alta', 'urgente')
        if valor in prioridades_validas:
            anterior = ticket.prioridad
            ticket.prioridad = valor
            ticket.updated_at = datetime.utcnow()
            registrar_historial(ticket_id, 'Prioridad actualizada', anterior, valor)
            db.session.commit()
            flash(f'Prioridad actualizada a "{ticket.prioridad_label}".', 'success')

    elif campo == 'asignado' and current_user.is_agente():
        agente_id = int(valor) if valor and valor != '0' else None
        anterior_id = ticket.assigned_to
        anterior_nombre = ticket.assignee.username if ticket.assignee else 'Sin asignar'
        ticket.assigned_to = agente_id
        ticket.updated_at = datetime.utcnow()
        if agente_id:
            agente = User.query.get(agente_id)
            nuevo_nombre = agente.username if agente else 'Desconocido'
        else:
            nuevo_nombre = 'Sin asignar'
        registrar_historial(ticket_id, 'Asignación actualizada', anterior_nombre, nuevo_nombre)
        db.session.commit()
        flash('Ticket reasignado correctamente.', 'success')

    return redirect(url_for('tickets.ticket_detalle', ticket_id=ticket_id))


@tickets_bp.route('/tickets/<int:ticket_id>/eliminar', methods=['POST'])
@login_required
def eliminar_ticket(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    if not current_user.is_agente():
        abort(403)
    db.session.delete(ticket)
    db.session.commit()
    flash('Ticket eliminado.', 'info')
    return redirect(url_for('tickets.tickets'))
