from flask import Blueprint, request, jsonify, render_template
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.models import User, Wallet, Transaction
from app import db
from datetime import datetime

wallet_bp = Blueprint('wallet', __name__, url_prefix='/api/wallet')

from datetime import datetime, timedelta

def detect_fraud(user_id, txn_type, amount):
    now = datetime.utcnow()
    one_min_ago = now - timedelta(minutes=1)

    # Rule 1: Multiple transfers in a short period
    recent_transfers = Transaction.query.filter_by(
        sender_id=user_id,
        type='transfer_out'
    ).filter(Transaction.timestamp >= one_min_ago).count()

    if txn_type == 'transfer_out' and recent_transfers >= 3:
        return 'rapid_transfers'

    # Rule 2: Sudden large withdrawal
    if txn_type == 'withdraw' and amount >= 10000:  # threshold
        return 'large_withdrawal'

    return None  # No fraud detected


@wallet_bp.route('/ping', methods=['GET'])
@jwt_required()
def ping():
    current_user = get_jwt_identity()
    user = User.query.filter_by(username=current_user).first()
    return jsonify({'message': f'Wallet is reachable by {user.username}'}), 200


@wallet_bp.route('/deposit', methods=['POST'])
@jwt_required()
def deposit():
    data = request.get_json()
    amount = data.get('amount')
    currency = data.get('currency', 'INR').upper()

    if amount is None or amount <= 0:
        return jsonify({'msg': 'Invalid deposit amount'}), 400

    user = User.query.filter_by(username=get_jwt_identity()).first()

    wallet = Wallet.query.filter_by(user_id=user.id, currency=currency).first()
    if not wallet:
        wallet = Wallet(user_id=user.id, currency=currency, balance=0.0)
        db.session.add(wallet)

    wallet.balance += amount

    transaction = Transaction(
        type='deposit',
        amount=amount,
        currency=currency,
        sender_id=user.id,
        timestamp=datetime.utcnow()
    )

    db.session.add(transaction)
    db.session.commit()

    return jsonify({'msg': f'{amount} {currency} deposited successfully', 'balance': wallet.balance}), 200


@wallet_bp.route('/withdraw', methods=['POST'])
@jwt_required()
def withdraw():
    data = request.get_json()
    amount = data.get('amount')
    currency = data.get('currency', 'INR').upper()

    if amount is None or amount <= 0:
        return jsonify({'msg': 'Invalid withdrawal amount'}), 400

    user = User.query.filter_by(username=get_jwt_identity()).first()

    wallet = Wallet.query.filter_by(user_id=user.id, currency=currency).first()
    if not wallet or wallet.balance < amount:
        return jsonify({'msg': 'Insufficient balance'}), 400
    
    flag = detect_fraud(user.id, 'withdraw', amount)

    wallet.balance -= amount

    transaction = Transaction(
        type='withdraw',
        amount=amount,
        sender_id=user.id,
        currency=currency,
        flag=flag,
        timestamp=datetime.utcnow()
    )

    db.session.add(transaction)
    db.session.commit()

    return jsonify({'msg': f'{amount} {currency} withdrawn successfully','balance': wallet.balance}), 200


@wallet_bp.route('/transfer', methods=['POST'])
@jwt_required()
def transfer():
    data = request.get_json()
    amount = data.get('amount')
    recipient_username = data.get('to')
    currency = data.get('currency', 'INR').upper()

    if amount is None or amount <= 0 or not recipient_username:
        return jsonify({'msg': 'Invalid transfer details'}), 400

    sender = User.query.filter_by(username=get_jwt_identity()).first()
    recipient = User.query.filter_by(username=recipient_username).first()

    if not recipient:
        return jsonify({'msg': 'Recipient user not found'}), 404

    sender_wallet = Wallet.query.filter_by(user_id=sender.id, currency=currency).first()
    recipient_wallet = Wallet.query.filter_by(user_id=recipient.id, currency=currency).first()

    if not sender_wallet or sender_wallet.balance < amount:
        return jsonify({'msg': 'Insufficient funds'}), 400

    if not recipient_wallet:
        recipient_wallet = Wallet(user_id=recipient.id, currency=currency, balance=0.0)
        db.session.add(recipient_wallet)

    sender_wallet.balance -= amount
    recipient_wallet.balance += amount

    flag = detect_fraud(sender.id, 'transfer_out', amount)

    db.session.add(Transaction(
        type='transfer_out',
        amount=amount,
        sender_id=sender.id,
        receiver_id=recipient.id,
        currency=currency,
        flag=flag,
        timestamp=datetime.utcnow()
    ))

    db.session.add(Transaction(
        type='transfer_in',
        amount=amount,
        currency=currency,
        sender_id=sender.id,
        receiver_id=recipient.id,
        timestamp=datetime.utcnow()
    ))

    db.session.commit()

    return jsonify({'msg': f'{amount} {currency} transferred to {recipient_username}'}), 200


@wallet_bp.route('/history', methods=['GET'])
@jwt_required()
def transaction_history():
    current_user = get_jwt_identity()
    user = User.query.filter_by(username=current_user).first()
    if not user:
        return jsonify({'msg': 'User not found'}), 404

    transactions = Transaction.query.filter(
        (Transaction.sender_id == user.id) | (Transaction.receiver_id == user.id)
    ).order_by(Transaction.timestamp.desc()).all()

    history = []
    for txn in transactions:
        direction = "outgoing" if txn.sender_id == user.id else "incoming"
        history.append({
            'id': txn.id,
            'type': txn.type,
            'amount': txn.amount,
            'currency': txn.currency,
            'timestamp': txn.timestamp.isoformat(),
            'sender': txn.sender_id,
            'receiver': txn.receiver_id,
            'flag': txn.flag
        })

    return jsonify({'transactions': history})
