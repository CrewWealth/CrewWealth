from flask import Blueprint, jsonify, request
from firebase_admin import auth as firebase_auth, firestore
from functools import wraps
from datetime import datetime, timezone

api_bp = Blueprint('api', __name__, url_prefix='/api')


def require_firebase_token(f):
    """Decorator: validates Firebase ID token from Authorization header."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid Authorization header'}), 401
        id_token = auth_header.split('Bearer ', 1)[1].strip()
        try:
            decoded = firebase_auth.verify_id_token(id_token)
        except Exception:
            return jsonify({'error': 'Invalid or expired token'}), 401
        # Attach verified uid to request context
        request.verified_uid = decoded['uid']
        return f(*args, **kwargs)
    return decorated


@api_bp.route('/projection/<uid>', methods=['GET'])
@require_firebase_token
def get_projection(uid):
    """
    Returns a 36-month (3-year) wealth projection for the authenticated user.

    The uid in the URL is cross-checked against the verified token uid so that
    users can only access their own projection data.

    Query params:
      starting_balance (float, optional): Override starting balance. Defaults
        to the sum of the user's account balances read from Firestore.
    """
    if request.verified_uid != uid:
        return jsonify({'error': 'Forbidden: uid mismatch'}), 403

    db = firestore.client()
    user_ref = db.collection('users').doc(uid)

    # ── 1. Starting balance (sum of all accounts) ──────────────────────────
    try:
        accounts_snap = user_ref.collection('accounts').get()
        starting_balance = sum(
            float(doc.to_dict().get('balance', 0) or 0)
            for doc in accounts_snap
        )
    except Exception:
        starting_balance = 0.0

    # Allow client override (e.g. when no accounts exist yet)
    try:
        override = request.args.get('starting_balance')
        if override is not None:
            starting_balance = float(override)
    except (ValueError, TypeError):
        pass

    # ── 2. Monthly net (income − spending) from last 3 months ─────────────
    now = datetime.now(timezone.utc)
    three_months_ago = datetime(
        now.year if now.month > 3 else now.year - 1,
        (now.month - 3) % 12 or 12,
        1,
        tzinfo=timezone.utc
    )

    try:
        tx_snap = (
            user_ref.collection('transactions')
            .where('date', '>=', three_months_ago)
            .get()
        )
        total_income = 0.0
        total_spending = 0.0
        monthly_buckets: dict[str, dict] = {}

        for doc in tx_snap:
            tx = doc.to_dict()
            amount = abs(float(tx.get('amount', 0) or 0))
            date = tx.get('date')
            if date is None:
                continue
            # Firestore timestamp → datetime
            if hasattr(date, 'todate'):
                date = date.todate()
            elif hasattr(date, 'datetime'):
                date = date.datetime
            else:
                # already a datetime or similar
                try:
                    date = date.astimezone(timezone.utc)
                except Exception:
                    pass

            month_key = f"{date.year}-{date.month:02d}" if hasattr(date, 'year') else None
            if month_key:
                monthly_buckets.setdefault(month_key, {'income': 0.0, 'spending': 0.0})

            tx_type = tx.get('type', '')
            if tx_type in ('salary', 'deposit'):
                total_income += amount
                if month_key:
                    monthly_buckets[month_key]['income'] += amount
            elif tx_type == 'payment':
                total_spending += amount
                if month_key:
                    monthly_buckets[month_key]['spending'] += amount

        months_with_data = len(monthly_buckets) or 1
        monthly_net = (total_income - total_spending) / months_with_data

    except Exception:
        monthly_net = 0.0

    # ── 3. Build 36-month projection ──────────────────────────────────────
    labels = []
    balances = []
    balance = starting_balance

    for i in range(36):
        # Advance one month from *now*
        target_month = now.month + i
        target_year = now.year + (target_month - 1) // 12
        target_month = (target_month - 1) % 12 + 1
        label = datetime(target_year, target_month, 1).strftime('%b %Y')
        balance += monthly_net
        labels.append(label)
        balances.append(round(balance, 2))

    return jsonify({
        'uid': uid,
        'starting_balance': round(starting_balance, 2),
        'monthly_net': round(monthly_net, 2),
        'balance_12m': balances[11] if len(balances) >= 12 else None,
        'balance_24m': balances[23] if len(balances) >= 24 else None,
        'balance_36m': balances[35] if len(balances) >= 36 else None,
        'labels': labels,
        'balances': balances,
    })
