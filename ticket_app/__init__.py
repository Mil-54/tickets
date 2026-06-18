import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate
from dotenv import load_dotenv

# Load env variables from .env
load_dotenv()

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
migrate = Migrate()

def create_app(config_name=None):
    """Application factory function."""
    app = Flask(__name__)
    
    # Load configuration
    from config import config_by_name
    if not config_name:
        config_name = os.environ.get('FLASK_ENV', 'development')
    app.config.from_object(config_by_name.get(config_name, config_by_name['default']))
    
    # Initialize extensions with app context
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)
    
    # Configure LoginManager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Por favor inicia sesión para continuar.'
    login_manager.login_message_category = 'warning'
    
    # Register user loader
    from ticket_app.models import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Register blueprints
    from ticket_app.blueprints.auth.routes import auth_bp
    from ticket_app.blueprints.tickets.routes import tickets_bp
    from ticket_app.blueprints.admin.routes import admin_bp
    from ticket_app.blueprints.api.routes import api_bp
    from ticket_app.blueprints.main.routes import main_bp
    from ticket_app.blueprints.errors.handlers import errors_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(tickets_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(errors_bp)
    
    # Configure logging
    configure_logging(app)
    
    # Register CLI commands
    from ticket_app.commands import seed_db
    app.cli.add_command(seed_db)
    
    return app

def configure_logging(app):
    """Setup logging for the application."""
    if not os.path.exists('logs'):
        os.mkdir('logs')
        
    file_handler = RotatingFileHandler(
        'logs/ticket_system.log',
        maxBytes=102400, # 100KB
        backupCount=10
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    
    if app.debug:
        app.logger.setLevel(logging.DEBUG)
    else:
        app.logger.setLevel(logging.INFO)
    app.logger.info('TicketFlow Startup')
