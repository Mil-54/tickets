# pyrefly: ignore [missing-import]
from flask import (
    Flask, render_template, redirect, url_for,
    request, flash, jsonify, abort
)
from flask_login import (
    LoginManager, login_user, logout_user,
    login_required, current_user
)
from models import db, User, Ticket, Comment, TicketHistory
from datetime import datetime
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ticket-system-secret-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tickets.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Por favor inicia sesión para continuar.'
login_manager.login_message_category = 'warning'

CATEGORIAS = [
    'Soporte Técnico',
    'Facturación',
    'Consulta General',
    'Bug / Error',
    'Solicitud de Función',
    'Acceso / Permisos',
    'Otro',
]

COLORES_AVATAR = [
    '#7C3AED', '#2563EB', '#059669', '#DC2626',
    '#D97706', '#DB2777', '#0891B2', '#65A30D'
]


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ─── Helpers ────────────────────────────────────────────────────────────────

def registrar_historial(ticket_id, accion, anterior=None, nuevo=None):
    h = TicketHistory(
        ticket_id=ticket_id,
        user_id=current_user.id,
        accion=accion,
        valor_anterior=anterior,
        valor_nuevo=nuevo
    )
    db.session.add(h)


# ─── Auth ────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            if not user.is_active:
                flash('Tu cuenta está desactivada. Contacta al administrador.', 'error')
                return redirect(url_for('login'))
            login_user(user, remember=True)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        flash('Correo o contraseña incorrectos.', 'error')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

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
            user = User(
                username=username,
                email=email,
                role=role,
                avatar_color=random.choice(COLORES_AVATAR)
            )
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user, remember=True)
            flash(f'¡Bienvenido, {username}!', 'success')
            return redirect(url_for('dashboard'))

    return render_template('register.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión correctamente.', 'info')
    return redirect(url_for('login'))


# ─── Dashboard ───────────────────────────────────────────────────────────────

@app.route('/dashboard')
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
        for cat in CATEGORIAS:
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


# ─── Tickets ─────────────────────────────────────────────────────────────────

@app.route('/tickets')
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
            db.or_(
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

    return render_template(
        'tickets.html',
        tickets=pagination.items,
        pagination=pagination,
        categorias=CATEGORIAS,
        agentes=agentes,
        filtros={
            'estado': estado_f,
            'prioridad': prioridad_f,
            'categoria': categoria_f,
            'asignado': asignado_f,
            'q': busqueda,
        }
    )


@app.route('/tickets/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_ticket():
    if request.method == 'POST':
        titulo = request.form.get('titulo', '').strip()
        descripcion = request.form.get('descripcion', '').strip()
        categoria = request.form.get('categoria', '')
        prioridad = request.form.get('prioridad', 'media')

        if not titulo or not descripcion or not categoria:
            flash('Todos los campos son obligatorios.', 'error')
        elif categoria not in CATEGORIAS:
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
            return redirect(url_for('ticket_detalle', ticket_id=ticket.id))

    return render_template('new_ticket.html', categorias=CATEGORIAS)


@app.route('/tickets/<int:ticket_id>')
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


@app.route('/tickets/<int:ticket_id>/comentar', methods=['POST'])
@login_required
def comentar_ticket(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)

    if not current_user.is_agente() and ticket.created_by != current_user.id:
        abort(403)

    contenido = request.form.get('contenido', '').strip()
    es_interno = request.form.get('es_interno') == 'on' and current_user.is_agente()

    if not contenido:
        flash('El comentario no puede estar vacío.', 'error')
        return redirect(url_for('ticket_detalle', ticket_id=ticket_id))

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
    return redirect(url_for('ticket_detalle', ticket_id=ticket_id))


@app.route('/tickets/<int:ticket_id>/actualizar', methods=['POST'])
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

    return redirect(url_for('ticket_detalle', ticket_id=ticket_id))


@app.route('/tickets/<int:ticket_id>/eliminar', methods=['POST'])
@login_required
def eliminar_ticket(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    if not current_user.is_agente():
        abort(403)
    db.session.delete(ticket)
    db.session.commit()
    flash('Ticket eliminado.', 'info')
    return redirect(url_for('tickets'))


# ─── Admin ───────────────────────────────────────────────────────────────────

@app.route('/admin/usuarios')
@login_required
def admin_usuarios():
    if not current_user.is_agente():
        abort(403)
    usuarios = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin.html', usuarios=usuarios)


@app.route('/admin/usuarios/<int:user_id>/toggle', methods=['POST'])
@login_required
def toggle_usuario(user_id):
    if not current_user.is_agente():
        abort(403)
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('No puedes desactivar tu propia cuenta.', 'error')
        return redirect(url_for('admin_usuarios'))
    user.is_active = not user.is_active
    db.session.commit()
    estado = 'activado' if user.is_active else 'desactivado'
    flash(f'Usuario {user.username} {estado}.', 'success')
    return redirect(url_for('admin_usuarios'))


@app.route('/admin/usuarios/<int:user_id>/rol', methods=['POST'])
@login_required
def cambiar_rol(user_id):
    if not current_user.is_agente():
        abort(403)
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('No puedes cambiar tu propio rol.', 'error')
        return redirect(url_for('admin_usuarios'))
    nuevo_rol = 'agente' if user.role == 'cliente' else 'cliente'
    user.role = nuevo_rol
    db.session.commit()
    flash(f'Rol de {user.username} cambiado a {nuevo_rol}.', 'success')
    return redirect(url_for('admin_usuarios'))


# ─── API JSON ─────────────────────────────────────────────────────────────────

@app.route('/api/stats')
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


# ─── Seed ─────────────────────────────────────────────────────────────────────

def seed_data():
    """Poblar con datos de ejemplo."""
    if User.query.count() > 0:
        return

    import random

    # Agentes
    agente1 = User(username='Carlos Admin', email='admin@demo.com',
                   role='agente', avatar_color='#7C3AED')
    agente1.set_password('admin123')

    agente2 = User(username='Laura Gómez', email='laura@demo.com',
                   role='agente', avatar_color='#2563EB')
    agente2.set_password('admin123')

    # Clientes
    clientes_data = [
        ('Ana Martínez', 'ana@demo.com', '#059669'),
        ('Pedro Ruiz', 'pedro@demo.com', '#DC2626'),
        ('María Torres', 'maria@demo.com', '#D97706'),
        ('Juan López', 'juan@demo.com', '#DB2777'),
    ]
    clientes = []
    for nombre, email, color in clientes_data:
        c = User(username=nombre, email=email, role='cliente', avatar_color=color)
        c.set_password('cliente123')
        clientes.append(c)

    db.session.add_all([agente1, agente2] + clientes)
    db.session.flush()

    # Tickets de ejemplo
    tickets_data = [
        ('No puedo acceder a mi cuenta', 'Desde ayer no me deja iniciar sesión. He intentado restablecer la contraseña pero tampoco funciona.', 'Acceso / Permisos', 'alta', 'abierto'),
        ('Error al procesar pago', 'Al intentar realizar el pago con tarjeta de crédito aparece el mensaje "Error 500". He probado con dos tarjetas diferentes.', 'Facturación', 'urgente', 'en_progreso'),
        ('¿Cómo exporto mis datos?', 'Necesito exportar mi historial completo en formato CSV para hacer una auditoría interna.', 'Consulta General', 'baja', 'resuelto'),
        ('El botón de guardar no funciona', 'En el formulario de perfil, el botón "Guardar cambios" no hace nada al hacer clic. Firefox 120.', 'Bug / Error', 'media', 'abierto'),
        ('Solicitud de factura electrónica', 'Necesito la factura electrónica del mes de abril para presentarla ante la DIAN.', 'Facturación', 'media', 'abierto'),
        ('Lentitud en la plataforma', 'La aplicación está muy lenta desde hace tres días, especialmente en las horas de la tarde.', 'Soporte Técnico', 'alta', 'en_progreso'),
        ('Agregar modo oscuro', 'Sería muy útil tener una opción de modo oscuro para trabajar de noche sin cansarse la vista.', 'Solicitud de Función', 'baja', 'cerrado'),
        ('Error al subir archivos PDF', 'Cuando intento subir un PDF mayor a 5MB muestra un error, pero el límite según la documentación es 20MB.', 'Bug / Error', 'alta', 'resuelto'),
        ('Capacitación sobre nuevas funciones', 'Quisiera que alguien nos explicara las nuevas funcionalidades del módulo de reportes.', 'Consulta General', 'baja', 'abierto'),
        ('Doble cobro en mi tarjeta', '¡URGENTE! Se realizaron dos cobros de $200.000 en mi tarjeta el día de ayer. Necesito solución inmediata.', 'Facturación', 'urgente', 'en_progreso'),
    ]

    agentes_list = [agente1, agente2]
    for i, (titulo, desc, cat, prior, estado) in enumerate(tickets_data):
        cliente = random.choice(clientes)
        agente_asignado = random.choice(agentes_list) if estado != 'abierto' else None
        t = Ticket(
            titulo=titulo,
            descripcion=desc,
            categoria=cat,
            prioridad=prior,
            estado=estado,
            created_by=cliente.id,
            assigned_to=agente_asignado.id if agente_asignado else None,
        )
        db.session.add(t)
        db.session.flush()

        # Historial inicial
        h = TicketHistory(ticket_id=t.id, user_id=cliente.id,
                          accion='Ticket creado')
        db.session.add(h)

        # Algunos comentarios
        if i % 2 == 0:
            c = Comment(ticket_id=t.id, user_id=cliente.id,
                        contenido='Adjunto más información sobre el problema que mencioné.',
                        es_interno=False)
            db.session.add(c)
        if agente_asignado and i % 3 == 0:
            c2 = Comment(ticket_id=t.id, user_id=agente_asignado.id,
                         contenido='Hemos recibido tu reporte y estamos revisando el caso. Te notificaremos pronto.',
                         es_interno=False)
            db.session.add(c2)
            c3 = Comment(ticket_id=t.id, user_id=agente_asignado.id,
                         contenido='Nota interna: revisar logs del servidor entre 14:00 y 16:00.',
                         es_interno=True)
            db.session.add(c3)

    db.session.commit()
    print('✅ Datos de ejemplo cargados.')
    print('   Agente:  admin@demo.com / admin123')
    print('   Cliente: ana@demo.com / cliente123')


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_data()
    app.run(debug=True, port=5050)
