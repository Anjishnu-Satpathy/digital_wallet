from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_cors import CORS

db = SQLAlchemy()
jwt = JWTManager()

def create_app():
    app = Flask(__name__)

    app.config['SECRET_KEY'] = 'super-secret-key'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///wallet.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = 'jwt-secret-key'

    db.init_app(app)
    jwt.init_app(app)

    CORS(app, resources={r"/api/*": {"origins": "http://127.0.0.1:5500"}})

    from app.models import models

    from app.routes.auth import auth_bp
    app.register_blueprint(auth_bp)

    from app.routes.wallet import wallet_bp
    app.register_blueprint(wallet_bp, url_prefix='/api/wallet')

    from app.routes.admin import admin_bp
    app.register_blueprint(admin_bp)


    return app