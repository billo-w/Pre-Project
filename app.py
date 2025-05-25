import os
import json
import logging
import requests
from dotenv import load_dotenv
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, UserMixin
from flask_wtf import FlaskForm, CSRFProtect
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
from werkzeug.security import generate_password_hash, check_password_hash

# --- Basic Setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()

# --- Extensions ---
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()

# --- API Constants ---
ADZUNA_APP_ID = os.getenv('ADZUNA_APP_ID')
ADZUNA_APP_KEY = os.getenv('ADZUNA_APP_KEY')
AZURE_AI_ENDPOINT = os.getenv('AZURE_AI_ENDPOINT')
AZURE_AI_KEY = os.getenv('AZURE_AI_KEY')
ADZUNA_API_BASE_URL = 'https://api.adzuna.com/v1/api/jobs'
RESULTS_PER_PAGE = 20

# --- Models ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    saved_jobs = db.relationship('SavedJob', backref='user', cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class SavedJob(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    adzuna_job_id = db.Column(db.String(100), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    company = db.Column(db.String(150))
    location = db.Column(db.String(150))
    adzuna_url = db.Column(db.String(500))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    __table_args__ = (db.UniqueConstraint('user_id', 'adzuna_job_id', name='_user_job_uc'),)

# --- Forms ---
class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_email(self, email):
        if User.query.filter_by(email=email.data).first():
            raise ValidationError('Email already registered.')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

# --- App Factory ---
def create_app(config_object=None):
    app = Flask(__name__, template_folder='templates')
    app.config.update(
        SECRET_KEY=os.getenv('FLASK_SECRET_KEY', 'dev-secret'),
        SQLALCHEMY_DATABASE_URI=os.getenv('DATABASE_URL'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        WTF_CSRF_ENABLED=True,
        TESTING=os.getenv('TESTING', 'False').lower() in ('true', '1'),
        LOGIN_DISABLED=os.getenv('LOGIN_DISABLED', 'False').lower() in ('true', '1')
    )

    if config_object:
        app.config.from_object(config_object)

    # --- Extensions Init ---
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = 'main_bp.login'

    from routes import main_bp
    app.register_blueprint(main_bp)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    return app

# --- Helper: Salary Histogram ---
def get_salary_histogram(country, location, title):
    if not (ADZUNA_APP_ID and ADZUNA_APP_KEY):
        return None

    try:
        url = f"{ADZUNA_API_BASE_URL}/{country.lower()}/histogram"
        params = {'app_id': ADZUNA_APP_ID, 'app_key': ADZUNA_APP_KEY, 'location0': location, 'what': title}
        res = requests.get(url, params=params, timeout=10)
        res.raise_for_status()
        data = res.json().get('histogram', {})
        if not data:
            return None

        avg = sum(float(k) * v for k, v in data.items()) / sum(data.values())
        return {'histogram': data, 'average': round(avg)}
    except Exception as e:
        logger.warning(f"Salary histogram error: {e}")
        return None

# --- Helper: Azure AI Summary ---
def get_ai_summary(query, total_jobs, listings, salary_data):
    if not (AZURE_AI_ENDPOINT and AZURE_AI_KEY):
        return None

    sample_titles = [job['title'] for job in listings[:5]]
    sample_desc = "\n---\n".join(job.get('description', '') for job in listings[:5])[:1500]

    salary_text = (
        f"approx. {salary_data['average']:,}" if salary_data and 'average' in salary_data
        else "Not available"
    )

    prompt = {
        "messages": [
            {"role": "system", "content": "You are an AI assistant..."},
            {"role": "user", "content": f"Analyze jobs for '{query['what']}' in '{query['where']}'..."}
        ],
        "max_tokens": 350,
        "temperature": 0.3
    }

    try:
        response = requests.post(
            AZURE_AI_ENDPOINT,
            headers={"Content-Type": "application/json", "api-key": AZURE_AI_KEY},
            json=prompt
        )
        return response.json()
    except Exception as e:
        logger.warning(f"Azure AI error: {e}")
        return None
