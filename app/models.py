from . import db # Import db from app package's __init__
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash
import math
from datetime import date

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)
    score = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=db.func.now())
    total_questions_answered = db.Column(db.Integer, default=0)
    correct_answers_count = db.Column(db.Integer, default=0)
    highest_streak = db.Column(db.Integer, default=0)
    games_played = db.Column(db.Integer, default=0)

    # XP & Level system
    xp = db.Column(db.Integer, default=0)
    daily_streak = db.Column(db.Integer, default=0)
    last_daily_date = db.Column(db.Date, nullable=True)
    last_login_date = db.Column(db.Date, nullable=True)
    countries_collected = db.Column(db.Integer, default=0)

    achievements = relationship("UserAchievement", back_populates="user_relation", cascade="all, delete-orphan")
    collected_countries = relationship("CollectedCountry", back_populates="user_relation", cascade="all, delete-orphan")
    region_progress = relationship("RegionProgress", back_populates="user_relation", cascade="all, delete-orphan")

    @property
    def level(self):
        """Level = floor(sqrt(xp / 50)) + 1, so L2 at 50 XP, L3 at 200, L4 at 450..."""
        return int(math.floor(math.sqrt((self.xp or 0) / 50))) + 1

    @property
    def xp_for_current_level(self):
        """XP threshold to reach current level."""
        lvl = self.level
        return ((lvl - 1) ** 2) * 50

    @property
    def xp_for_next_level(self):
        """XP threshold to reach next level."""
        lvl = self.level
        return (lvl ** 2) * 50

    @property
    def xp_progress_pct(self):
        """Percentage progress toward next level (0-100)."""
        current = self.xp_for_current_level
        nxt = self.xp_for_next_level
        if nxt == current:
            return 100
        return round(((self.xp or 0) - current) / (nxt - current) * 100)

    RANK_TABLE = [
        (1, "Map Rookie", "🗺️"),
        (3, "Trail Scout", "🥾"),
        (5, "Continent Scout", "🧭"),
        (8, "Globe Trotter", "✈️"),
        (12, "World Sage", "📚"),
        (16, "Grand Explorer", "🔭"),
        (20, "Atlas Legend", "👑"),
    ]

    @property
    def rank_name(self):
        name = "Map Rookie"
        for lvl_req, r_name, _ in self.RANK_TABLE:
            if self.level >= lvl_req:
                name = r_name
        return name

    @property
    def rank_icon(self):
        icon = "🗺️"
        for lvl_req, _, r_icon in self.RANK_TABLE:
            if self.level >= lvl_req:
                icon = r_icon
        return icon

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class UserAchievement(db.Model):
    __tablename__ = 'user_achievement'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    achievement_id = db.Column(db.String(100), nullable=False)
    unlocked_at = db.Column(db.DateTime, default=db.func.now())

    user_relation = relationship("User", back_populates="achievements")

    def __repr__(self):
        return f'<UserAchievement {self.user_id} - {self.achievement_id}>'

class Continent(db.Model):
    __tablename__ = 'continent'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    area_sq_km = db.Column(db.Float, nullable=True)
    population = db.Column(db.BigInteger, nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    timezones = db.Column(db.Text, nullable=True)
    highest_point = db.Column(db.String(200), nullable=True)
    lowest_point = db.Column(db.String(200), nullable=True)
    countries = relationship("Country", back_populates="continent_relation")

    def __repr__(self):
        return f'<Continent {self.name}>'

class Country(db.Model):
    __tablename__ = 'country'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    cca3 = db.Column(db.String(3), unique=True, nullable=True)
    official_name = db.Column(db.String(255), nullable=True)
    capital = db.Column(db.String(100), nullable=True)
    population = db.Column(db.BigInteger, nullable=True)
    area = db.Column(db.Float, nullable=True)
    region = db.Column(db.String(100), nullable=True)
    subregion = db.Column(db.String(100), nullable=True)
    flag_url_png = db.Column(db.String(255), nullable=True)
    flag_url_svg = db.Column(db.String(255), nullable=True)
    coat_of_arms_url_png = db.Column(db.String(255), nullable=True)
    coat_of_arms_url_svg = db.Column(db.String(255), nullable=True)
    currencies = db.Column(db.JSON, nullable=True)
    languages = db.Column(db.JSON, nullable=True)
    maps_google = db.Column(db.String(255), nullable=True)
    maps_osm = db.Column(db.String(255), nullable=True)
    
    continent_name = db.Column(db.String(100), db.ForeignKey('continent.name'))
    continent_relation = relationship("Continent", back_populates="countries")

    trivia = db.Column(db.Text, nullable=True)

    # New fields from REST Countries API
    borders = db.Column(db.JSON, nullable=True)        # List of bordering country codes
    landlocked = db.Column(db.Boolean, nullable=True)
    timezones = db.Column(db.JSON, nullable=True)       # List of timezone strings
    demonyms = db.Column(db.String(100), nullable=True)  # What people are called
    driving_side = db.Column(db.String(10), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    start_of_week = db.Column(db.String(20), nullable=True)

    # Curated enrichment data
    gdp_billion_usd = db.Column(db.Float, nullable=True)
    key_cities = db.Column(db.Text, nullable=True)
    key_industries = db.Column(db.Text, nullable=True)
    fun_facts = db.Column(db.Text, nullable=True)
    famous_animals = db.Column(db.Text, nullable=True)
    climate = db.Column(db.Text, nullable=True)

    # Additional enriched fields
    gdp_ppp_billion_usd = db.Column(db.Float, nullable=True)
    gdp_per_capita_usd = db.Column(db.Integer, nullable=True)
    undp_hdi = db.Column(db.Float, nullable=True)
    hdi_ranking = db.Column(db.Integer, nullable=True)
    gdp_ranking = db.Column(db.Integer, nullable=True)

    provinces_states = db.Column(db.Text, nullable=True)
    major_rivers = db.Column(db.Text, nullable=True)
    major_mountains = db.Column(db.Text, nullable=True)
    national_animal = db.Column(db.String(100), nullable=True)
    national_sport = db.Column(db.String(100), nullable=True)
    national_bird = db.Column(db.String(100), nullable=True)

    # Cultural, economic, and physical landscape details
    state_religion = db.Column(db.String(100), nullable=True)
    major_religions = db.Column(db.Text, nullable=True)
    exports = db.Column(db.Text, nullable=True)
    imports = db.Column(db.Text, nullable=True)
    geographic_features = db.Column(db.Text, nullable=True)

    # Native & historic names
    native_name = db.Column(db.String(255), nullable=True)         # e.g. "Bharat" for India
    historic_name = db.Column(db.String(255), nullable=True)       # e.g. "Persia" for Iran

    # Greeting data
    hello_phrase = db.Column(db.String(200), nullable=True)        # "Bonjour"
    hello_pronunciation = db.Column(db.String(200), nullable=True) # "bon-ZHOOR"
    hello_language = db.Column(db.String(100), nullable=True)      # "French"

    def __repr__(self):
        return f'<Country {self.name}>'

class QuizQuestion(db.Model):
    __tablename__ = 'quiz_question'
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False) # e.g., 'capital', 'flag_to_country', 'country_to_flag'
    question_text = db.Column(db.String(255), nullable=False)
    # For flag questions, image_url_for_question can be country.flag_url_png
    image_url_for_question = db.Column(db.String(255), nullable=True)
    # Options are stored as separate columns or could be JSON if dynamic number of options
    option1 = db.Column(db.String(100), nullable=False)
    option2 = db.Column(db.String(100), nullable=False)
    option3 = db.Column(db.String(100), nullable=True)
    option4 = db.Column(db.String(100), nullable=True)
    correct_answer_value = db.Column(db.String(100), nullable=False) # Store the actual correct string
    difficulty = db.Column(db.Integer, default=1) # 1=easy, 2=medium, 3=hard

    def get_options_list(self):
        options = [self.option1, self.option2]
        if self.option3:
            options.append(self.option3)
        if self.option4:
            options.append(self.option4)
        return options

    def __repr__(self):
        return f'<QuizQuestion {self.question_text[:30]}...>'

# Geographic feature models
class Ocean(db.Model):
    __tablename__ = 'ocean'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    area_sq_km = db.Column(db.Float, nullable=True)
    avg_depth_m = db.Column(db.Integer, nullable=True)
    max_depth_m = db.Column(db.Integer, nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    description = db.Column(db.Text, nullable=True)

class Mountain(db.Model):
    __tablename__ = 'mountain'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    elevation_m = db.Column(db.Integer, nullable=True)
    location = db.Column(db.String(200), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    description = db.Column(db.Text, nullable=True)

class River(db.Model):
    __tablename__ = 'river'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    length_km = db.Column(db.Integer, nullable=True)
    location = db.Column(db.String(200), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    description = db.Column(db.Text, nullable=True)

class Forest(db.Model):
    __tablename__ = 'forest'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    area_sq_km = db.Column(db.Float, nullable=True)
    location = db.Column(db.String(200), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    description = db.Column(db.Text, nullable=True)

class Desert(db.Model):
    __tablename__ = 'desert'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    area_sq_km = db.Column(db.Float, nullable=True)
    location = db.Column(db.String(200), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    description = db.Column(db.Text, nullable=True)

class Volcano(db.Model):
    __tablename__ = 'volcano'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    elevation_m = db.Column(db.Integer, nullable=True)
    location = db.Column(db.String(200), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(50), nullable=True)  # Active, Dormant, Extinct
    description = db.Column(db.Text, nullable=True)

class Wonder(db.Model):
    __tablename__ = 'wonder'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), unique=True, nullable=False)
    location = db.Column(db.String(200), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    year_built = db.Column(db.String(100), nullable=True)
    description = db.Column(db.Text, nullable=True)


class CollectedCountry(db.Model):
    __tablename__ = 'collected_country'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    country_id = db.Column(db.Integer, db.ForeignKey('country.id'), nullable=False)
    collected_at = db.Column(db.DateTime, default=db.func.now())

    user_relation = relationship("User", back_populates="collected_countries")
    country_relation = relationship("Country")

    __table_args__ = (db.UniqueConstraint('user_id', 'country_id', name='_user_country_uc'),)


class RegionProgress(db.Model):
    __tablename__ = 'region_progress'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    region_name = db.Column(db.String(100), nullable=False)
    correct_count = db.Column(db.Integer, default=0)
    unlocked = db.Column(db.Boolean, default=False)

    user_relation = relationship("User", back_populates="region_progress")

    __table_args__ = (db.UniqueConstraint('user_id', 'region_name', name='_user_region_uc'),)


class DailyCompletion(db.Model):
    __tablename__ = 'daily_completion'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    completed_date = db.Column(db.Date, nullable=False)
    bonus_xp = db.Column(db.Integer, default=0)

    __table_args__ = (db.UniqueConstraint('user_id', 'completed_date', name='_user_daily_uc'),)


class QuizAttempt(db.Model):
    """Records every quiz answer for history, skill tracking, spaced repetition, and reports."""
    __tablename__ = 'quiz_attempt'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    country_id = db.Column(db.Integer, db.ForeignKey('country.id'), nullable=True)
    question_type = db.Column(db.String(50), nullable=False)   # capital, flag, population, area, continent, language, landlocked
    question_text = db.Column(db.String(500), nullable=False)
    submitted_answer = db.Column(db.String(200), nullable=False)
    correct_answer = db.Column(db.String(200), nullable=False)
    is_correct = db.Column(db.Boolean, nullable=False)
    time_taken_ms = db.Column(db.Integer, nullable=True)
    quiz_mode = db.Column(db.String(50), default='classic')
    created_at = db.Column(db.DateTime, default=db.func.now())

    user_relation = relationship("User", backref=db.backref("quiz_attempts", lazy="dynamic"))
    country_relation = relationship("Country")


class CountryMastery(db.Model):
    """Tracks mastery level (0-5 stars) per country per user, based on correct answers across categories."""
    __tablename__ = 'country_mastery'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    country_id = db.Column(db.Integer, db.ForeignKey('country.id'), nullable=False)
    stars = db.Column(db.Integer, default=0)                  # 0-5
    categories_correct = db.Column(db.JSON, default=list)     # e.g. ["capital", "flag", "continent"]
    total_correct = db.Column(db.Integer, default=0)
    total_attempts = db.Column(db.Integer, default=0)
    last_answered = db.Column(db.DateTime, default=db.func.now())

    user_relation = relationship("User", backref=db.backref("country_masteries", lazy="dynamic"))
    country_relation = relationship("Country")

    __table_args__ = (db.UniqueConstraint('user_id', 'country_id', name='_user_country_mastery_uc'),)


class MissionProgress(db.Model):
    """Tracks user progress through story mode missions."""
    __tablename__ = 'mission_progress'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    mission_id = db.Column(db.String(50), nullable=False)
    questions_completed = db.Column(db.Integer, default=0)
    correct_count = db.Column(db.Integer, default=0)
    completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    started_at = db.Column(db.DateTime, default=db.func.now())

    user_relation = relationship("User", backref=db.backref("mission_progress", lazy="dynamic"))

    __table_args__ = (db.UniqueConstraint('user_id', 'mission_id', name='_user_mission_uc'),)