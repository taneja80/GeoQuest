import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a_very_secret_key_for_dev'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'instance', 'geography.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    REST_COUNTRIES_API_URL = "https://restcountries.com/v3.1/independent?status=true"
    # Add other configurations here