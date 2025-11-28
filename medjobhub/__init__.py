from flask import Flask,send_from_directory, render_template, request, jsonify, redirect, send_file, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
import random
from datetime import datetime,timedelta
from flask_mail import Mail, Message
from random import randint
import secrets
import os
from io import BytesIO
from flask import session
from werkzeug.utils import secure_filename
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
import re,traceback
from flask_login import LoginManager,login_required
from flask_cors import CORS,cross_origin
from config import Config
from flask_restful import fields, marshal
from dotenv import load_dotenv
from flask_session import Session

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy()

db.init_app(app)

#http://medjobhub.com
allowed_url="https://medjobhub.vercel.app"

# allow both localhost domain variants for dev
CORS(app,
     resources={r"/*": {"origins": ["http://localhost:5173", "http://127.0.0.1:5173"]}},
     supports_credentials=True,
     methods=["GET", "POST", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization"]
     )

app.config.from_object(Config) 


login_manager=LoginManager(app)
login_manager.login_view='signin'
login_manager.login_message_category='sucess'
otp_storage = {}

upload_folder = os.path.join(os.getcwd(), 'uploads')
if not os.path.exists(upload_folder):
    os.makedirs(upload_folder)

app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_SECURE'] = True 
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "supersecret")

Session(app)



app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config['UPLOAD_FOLDER'] = upload_folder  
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'doc', 'docx', 'jpg', 'png'}

# Flask-Mail Configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = os.getenv('EMAIL_ID')
app.config['MAIL_PASSWORD'] = os.getenv('EMAIL_APP_PASSWORD')
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True


def allowed_file(filename):
    allowed_extensions = {'pdf', 'doc', 'docx', 'jpg', 'png'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

from medjobhub.models import User, Job, UserProfile,JobApplication
from medjobhub.routes import signin,signup,verify_otp,logout,job_cards,application_cards,contact_us,profile,ai_sorting,chatbot