import click
import random
from flask.cli import with_appcontext
from ticket_app import db
from ticket_app.models import User, Ticket, Comment, TicketHistory

@click.command("seed")
@with_appcontext
def seed_db():
    """Poblar la base de datos con datos de ejemplo."""
    if User.query.count() > 0:
        click.echo("La base de datos ya contiene datos.")
        return

    # Colores para avatares
    colores_avatar = [
        '#7C3AED', '#2563EB', '#059669', '#DC2626',
        '#D97706', '#DB2777', '#0891B2', '#65A30D'
    ]

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
    click.echo('✅ Datos de ejemplo cargados.')
    click.echo('   Agente:  admin@demo.com / admin123')
    click.echo('   Cliente: ana@demo.com / cliente123')
