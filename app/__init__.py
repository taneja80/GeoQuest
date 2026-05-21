from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate # Optional: for more complex migrations
from apscheduler.schedulers.background import BackgroundScheduler
import os

from config import Config

db = SQLAlchemy()
migrate = Migrate() # Optional

# Import models here to avoid circular imports in some cases,
# but ensure they are defined before db.create_all() is called.
# from . import models

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure instance folder exists for SQLite DB if it's placed there
    try:
        os.makedirs(app.instance_path, exist_ok=True)
        # If db is in 'data/' at root, adjust path or ensure 'data/' exists
        data_dir = os.path.join(app.root_path, '..', 'data')
        os.makedirs(data_dir, exist_ok=True)

    except OSError:
        pass # Should not happen with exist_ok=True

    db.init_app(app)
    migrate.init_app(app, db) # Optional

    from app.routes import main_bp
    app.register_blueprint(main_bp)

    # Import models here AFTER db is initialized and BEFORE create_all or first request
    # This is important for Flask CLI commands and for the app to know about models.
    with app.app_context():
        from . import models # Ensure models are imported so SQLAlchemy knows about them
        db.create_all() # Auto-create tables if they don't exist

    # Initialize and start scheduler
    from .data_updater import update_all_data_job
    scheduler = BackgroundScheduler()
    # Update data every 24 hours
    scheduler.add_job(func=update_all_data_job, args=[app], trigger="interval", hours=24)
    scheduler.start()
    
    # Shut down the scheduler when exiting the app
    import atexit
    atexit.register(lambda: scheduler.shutdown())

    return app