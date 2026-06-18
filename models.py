from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='cliente')  # 'agente' | 'cliente'
    avatar_color = db.Column(db.String(7), default='#7C3AED')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relaciones
    created_tickets = db.relationship(
        'Ticket', foreign_keys='Ticket.created_by', backref='creator', lazy=True
    )
    assigned_tickets = db.relationship(
        'Ticket', foreign_keys='Ticket.assigned_to', backref='assignee', lazy=True
    )
    comments = db.relationship('Comment', backref='author', lazy=True)
    history = db.relationship('TicketHistory', backref='actor', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def initials(self):
        parts = self.username.split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[1][0]).upper()
        return self.username[:2].upper()

    def is_agente(self):
        return self.role == 'agente'

    def __repr__(self):
        return f'<User {self.username}>'


class Ticket(db.Model):
    __tablename__ = 'tickets'

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    categoria = db.Column(db.String(50), nullable=False)
    prioridad = db.Column(db.String(20), nullable=False, default='media')
    # baja | media | alta | urgente
    estado = db.Column(db.String(20), nullable=False, default='abierto')
    # abierto | en_progreso | resuelto | cerrado
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)

    comments = db.relationship('Comment', backref='ticket', lazy=True,
                               cascade='all, delete-orphan', order_by='Comment.created_at')
    history = db.relationship('TicketHistory', backref='ticket', lazy=True,
                              cascade='all, delete-orphan', order_by='TicketHistory.created_at')

    @property
    def ticket_id(self):
        return f'TK-{str(self.id).zfill(4)}'

    @property
    def prioridad_label(self):
        labels = {
            'baja': 'Baja',
            'media': 'Media',
            'alta': 'Alta',
            'urgente': 'Urgente'
        }
        return labels.get(self.prioridad, self.prioridad)

    @property
    def estado_label(self):
        labels = {
            'abierto': 'Abierto',
            'en_progreso': 'En Progreso',
            'resuelto': 'Resuelto',
            'cerrado': 'Cerrado'
        }
        return labels.get(self.estado, self.estado)

    def __repr__(self):
        return f'<Ticket {self.ticket_id}: {self.titulo}>'


class Comment(db.Model):
    __tablename__ = 'comments'

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('tickets.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    contenido = db.Column(db.Text, nullable=False)
    es_interno = db.Column(db.Boolean, default=False)  # Solo visible para agentes
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Comment by {self.user_id} on ticket {self.ticket_id}>'


class TicketHistory(db.Model):
    __tablename__ = 'ticket_history'

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('tickets.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    accion = db.Column(db.String(100), nullable=False)
    valor_anterior = db.Column(db.String(100), nullable=True)
    valor_nuevo = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<History {self.accion} on ticket {self.ticket_id}>'
