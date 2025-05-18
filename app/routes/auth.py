from flask import Blueprint, request, jsonify
from app.models.models import User, Wallet
from app import db
from flask_jwt_extended import create_access_token

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'msg': 'User already exists'}), 409

    user = User(username=data['username'])
    user.set_password(data['password'])

    db.session.add(user)
    db.session.commit()

    wallet = Wallet(user_id=user.id, balance=0.0, currency='INR')
    db.session.add(wallet)
    db.session.commit()

    return jsonify({'msg': 'User registered successfully'}), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    # Input validation
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'msg': 'Username and password are required'}), 400

    # Lookup user
    user = User.query.filter_by(username=data['username']).first()
    if not user or not user.check_password(data['password']):
        return jsonify({'msg': 'Invalid credentials'}), 401

    # Generate JWT
    access_token = create_access_token(identity=user.username)
    return jsonify({'msg': 'Login successful', 'access_token': access_token}), 200
