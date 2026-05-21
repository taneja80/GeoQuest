from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate # Optional: for more complex migrations
import os
import datetime

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

    # Auto-update data on startup if stale (>24h) or empty
    _auto_update_if_stale(app)

    return app


def _auto_update_if_stale(app):
    """Update country data on startup if the DB is empty or data is older than 24 hours."""
    stamp_file = os.path.join(app.instance_path, '.last_data_update')
    needs_update = False

    with app.app_context():
        from .models import Country
        if Country.query.count() == 0:
            needs_update = True

    if not needs_update:
        if not os.path.exists(stamp_file):
            needs_update = True
        else:
            try:
                last = datetime.datetime.fromisoformat(open(stamp_file).read().strip())
                if datetime.datetime.now() - last > datetime.timedelta(hours=24):
                    needs_update = True
            except (ValueError, OSError):
                needs_update = True

    if needs_update:
        try:
            from .data_updater import update_all_data
            app.logger.info("Data is stale or missing — running auto-update...")
            update_all_data(app)
            with open(stamp_file, 'w') as f:
                f.write(datetime.datetime.now().isoformat())
            app.logger.info("Auto-update complete.")
        except Exception as e:
            app.logger.error(f"Auto-update failed: {e}")