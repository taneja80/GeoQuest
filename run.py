from app import create_app, db
from app.models import User, Country, Continent # Import all models you want to create tables for
from app.data_updater import update_all_data, init_continents

app = create_app()

@app.cli.command("init-db")
def init_db_command():
    """Creates the database tables."""
    with app.app_context():
        db.create_all()
        print("Initialized the database and created tables.")
        init_continents() # Initialize continents after table creation
        print("Initialized continents.")

@app.cli.command("update-data")
def update_data_command():
    """Updates data from live sources."""
    with app.app_context():
        print("Starting data update...")
        update_all_data()
        print("Data update complete.")

if __name__ == '__main__':
    # To initialize DB:
    # 1. Open terminal in geography_app directory
    # 2. Run: flask init-db
    # 3. Run: flask update-data (to fetch country data)
    # Then run the app:
    app.run(debug=True)