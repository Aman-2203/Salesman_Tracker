from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os

db = SQLAlchemy()
login_manager = LoginManager()


def create_app(config_class=None):
    app = Flask(__name__)

    if config_class is None:
        from config import Config
        app.config.from_object(Config)
    else:
        app.config.from_object(config_class)

    # Ensure upload folder exists
    os.makedirs(app.config.get('UPLOAD_FOLDER', 'uploads'), exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from app.timezone_utils import now_ist, today_ist, format_date, format_time, format_datetime

    # Jinja filters for GMT+5:30 dates and times
    app.jinja_env.filters['format_date'] = format_date
    app.jinja_env.filters['format_time'] = format_time
    app.jinja_env.filters['format_datetime'] = format_datetime

    @app.context_processor
    def inject_now():
        return {
            'now': now_ist(),
            'today': today_ist()
        }

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.admin import admin_bp
    from app.routes.rep import rep_bp
    from app.routes.visits import visits_bp
    from app.routes.orders import orders_bp
    from app.routes.attendance import attendance_bp
    from app.routes.customers import customers_bp
    from app.routes.payments import payments_bp
    from app.routes.api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(rep_bp, url_prefix='/rep')
    app.register_blueprint(visits_bp, url_prefix='/visits')
    app.register_blueprint(orders_bp, url_prefix='/orders')
    app.register_blueprint(attendance_bp, url_prefix='/attendance')
    app.register_blueprint(customers_bp, url_prefix='/customers')
    app.register_blueprint(payments_bp, url_prefix='/payments')
    app.register_blueprint(api_bp, url_prefix='/api')

    with app.app_context():
        db.create_all()

    return app
