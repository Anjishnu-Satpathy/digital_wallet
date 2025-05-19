from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.models import User, Wallet, Transaction
from app import db

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

def is_admin(user):
    return user and user.role == 'admin'

@admin_bp.route('/flagged-transactions', methods=['GET'])
@jwt_required()
def flagged_transactions():
    user = User.query.filter_by(username=get_jwt_identity()).first()
    if not is_admin(user):
        return jsonify({'msg': 'Access denied'}), 403

    flagged = Transaction.query.filter(Transaction.flag.isnot(None)).order_by(Transaction.timestamp.desc()).all()
    return jsonify({
        'flagged': [
            {
                'id': t.id,
                'type': t.type,
                'amount': t.amount,
                'currency': t.currency,
                'sender_id': t.sender_id,
                'receiver_id': t.receiver_id,
                'flag': t.flag,
                'timestamp': t.timestamp.isoformat()
            } for t in flagged
        ]
    })

@admin_bp.route('/top-users', methods=['GET'])
@jwt_required()
def top_users():
    user = User.query.filter_by(username=get_jwt_identity()).first()
    if not is_admin(user):
        return jsonify({'msg': 'Access denied'}), 403

    # Aggregate by balance
    top_balances = db.session.query(
        Wallet.user_id,
        db.func.sum(Wallet.balance).label('total_balance')
    ).group_by(Wallet.user_id).order_by(db.desc('total_balance')).limit(5).all()

    top_balance_data = [
        {
            'user_id': uid,
            'total_balance': bal,
            'username': User.query.get(uid).username
        }
        for uid, bal in top_balances
    ]

    return jsonify({'top_users_by_balance': top_balance_data})

@admin_bp.route('/total-balances', methods=['GET'])
@jwt_required()
def total_balances():
    user = User.query.filter_by(username=get_jwt_identity()).first()
    if not is_admin(user):
        return jsonify({'msg': 'Access denied'}), 403

    total = db.session.query(
        Wallet.currency,
        db.func.sum(Wallet.balance)
    ).group_by(Wallet.currency).all()

    return jsonify({
        'total_balances': [{ 'currency': cur, 'amount': amt } for cur, amt in total]
    })
