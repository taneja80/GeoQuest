import sqlite3
import os

def run_migration():
    db_path = os.path.join("instance", "geography.db")
    if not os.path.exists(db_path):
        print(f"Database file not found at {db_path}. It will be auto-created by Flask.")
        return

    print(f"Connecting to database at {db_path}...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. Update user table
    print("Updating 'user' table columns...")
    columns_to_add = [
        ("password_hash", "VARCHAR(255)"),
        ("created_at", "DATETIME"),
        ("total_questions_answered", "INTEGER DEFAULT 0"),
        ("correct_answers_count", "INTEGER DEFAULT 0"),
        ("highest_streak", "INTEGER DEFAULT 0"),
        ("games_played", "INTEGER DEFAULT 0"),
        ("xp", "INTEGER DEFAULT 0"),
        ("daily_streak", "INTEGER DEFAULT 0"),
        ("last_daily_date", "DATE"),
        ("last_login_date", "DATE"),
        ("countries_collected", "INTEGER DEFAULT 0"),
    ]

    # Get existing columns in user table
    cursor.execute("PRAGMA table_info(user)")
    existing_cols = [row[1] for row in cursor.fetchall()]

    for col_name, col_type in columns_to_add:
        if col_name not in existing_cols:
            print(f"Adding column '{col_name}' ({col_type}) to 'user' table...")
            cursor.execute(f"ALTER TABLE user ADD COLUMN {col_name} {col_type}")
        else:
            print(f"Column '{col_name}' already exists in 'user' table.")

    # 2. Create user_achievement table
    print("Creating 'user_achievement' table if it doesn't exist...")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_achievement (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        achievement_id VARCHAR(100) NOT NULL,
        unlocked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES user(id)
    )
    """)

    # 3. Create collected_country table
    print("Creating 'collected_country' table if it doesn't exist...")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS collected_country (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        country_id INTEGER NOT NULL,
        collected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES user(id),
        FOREIGN KEY(country_id) REFERENCES country(id),
        UNIQUE(user_id, country_id)
    )
    """)

    # 4. Create region_progress table
    print("Creating 'region_progress' table if it doesn't exist...")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS region_progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        region_name VARCHAR(100) NOT NULL,
        correct_count INTEGER DEFAULT 0,
        unlocked BOOLEAN DEFAULT 0,
        FOREIGN KEY(user_id) REFERENCES user(id),
        UNIQUE(user_id, region_name)
    )
    """)

    # 5. Create daily_completion table
    print("Creating 'daily_completion' table if it doesn't exist...")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS daily_completion (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        completed_date DATE NOT NULL,
        bonus_xp INTEGER DEFAULT 0,
        FOREIGN KEY(user_id) REFERENCES user(id),
        UNIQUE(user_id, completed_date)
    )
    """)

    # 6. Create quiz_attempt table
    print("Creating 'quiz_attempt' table if it doesn't exist...")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS quiz_attempt (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        country_id INTEGER,
        question_type VARCHAR(50) NOT NULL,
        question_text VARCHAR(500) NOT NULL,
        submitted_answer VARCHAR(200) NOT NULL,
        correct_answer VARCHAR(200) NOT NULL,
        is_correct BOOLEAN NOT NULL,
        time_taken_ms INTEGER,
        quiz_mode VARCHAR(50) DEFAULT 'classic',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES user(id),
        FOREIGN KEY(country_id) REFERENCES country(id)
    )
    """)

    # 7. Create country_mastery table
    print("Creating 'country_mastery' table if it doesn't exist...")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS country_mastery (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        country_id INTEGER NOT NULL,
        stars INTEGER DEFAULT 0,
        categories_correct TEXT DEFAULT '[]',
        total_correct INTEGER DEFAULT 0,
        total_attempts INTEGER DEFAULT 0,
        last_answered DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES user(id),
        FOREIGN KEY(country_id) REFERENCES country(id),
        UNIQUE(user_id, country_id)
    )
    """)

    # Backfill: set xp = score for existing users
    cursor.execute("UPDATE user SET xp = score WHERE xp IS NULL OR xp = 0")

    # 8. Create mission_progress table
    print("Creating 'mission_progress' table if it doesn't exist...")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mission_progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        mission_id VARCHAR(50) NOT NULL,
        questions_completed INTEGER DEFAULT 0,
        correct_count INTEGER DEFAULT 0,
        completed BOOLEAN DEFAULT 0,
        completed_at DATETIME,
        started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES user(id),
        UNIQUE(user_id, mission_id)
    )
    """)

    # 9. Add native/historic name and greeting columns to country table
    print("Adding native/historic name and greeting columns to 'country' table...")
    greeting_cols = [
        ("native_name", "VARCHAR(255)"),
        ("historic_name", "VARCHAR(255)"),
        ("hello_phrase", "VARCHAR(200)"),
        ("hello_pronunciation", "VARCHAR(200)"),
        ("hello_language", "VARCHAR(100)"),
    ]
    cursor.execute("PRAGMA table_info(country)")
    existing_country_cols = [row[1] for row in cursor.fetchall()]
    for col_name, col_type in greeting_cols:
        if col_name not in existing_country_cols:
            print(f"Adding column '{col_name}' to 'country' table...")
            cursor.execute(f"ALTER TABLE country ADD COLUMN {col_name} {col_type}")
        else:
            print(f"Column '{col_name}' already exists in 'country' table.")

    # 10. Add geographic enrichment columns to continent table
    print("Adding geographic columns to 'continent' table...")
    continent_cols = [
        ("area_sq_km", "FLOAT"),
        ("population", "BIGINT"),
        ("latitude", "FLOAT"),
        ("longitude", "FLOAT"),
        ("timezones", "TEXT"),
        ("highest_point", "VARCHAR(200)"),
        ("lowest_point", "VARCHAR(200)"),
    ]
    cursor.execute("PRAGMA table_info(continent)")
    existing_cont_cols = [row[1] for row in cursor.fetchall()]
    for col_name, col_type in continent_cols:
        if col_name not in existing_cont_cols:
            print(f"Adding column '{col_name}' to 'continent' table...")
            cursor.execute(f"ALTER TABLE continent ADD COLUMN {col_name} {col_type}")
        else:
            print(f"Column '{col_name}' already exists in 'continent' table.")

    # 11. Add lat/lng to geographic feature tables
    print("Adding coordinates to geographic feature tables...")
    geo_tables = ['ocean', 'mountain', 'river', 'forest', 'desert', 'volcano', 'wonder']
    for table_name in geo_tables:
        cursor.execute(f"PRAGMA table_info({table_name})")
        existing_cols = [row[1] for row in cursor.fetchall()]
        for col_name in ['latitude', 'longitude']:
            if col_name not in existing_cols:
                print(f"Adding column '{col_name}' to '{table_name}' table...")
                cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} FLOAT")
            else:
                print(f"Column '{col_name}' already exists in '{table_name}' table.")

    conn.commit()
    conn.close()
    print("Database migration successfully finished!")

if __name__ == "__main__":
    run_migration()
