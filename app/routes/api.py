import logging
import math
from flask import Blueprint, jsonify, request
from functools import wraps
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Import Firebase modules at module level; will be None if Firebase is not
# configured so that individual endpoints can return 503 instead of crashing.
try:
    from firebase_admin import auth as firebase_auth
    from firebase_admin import firestore as firebase_firestore
    from google.cloud.firestore_v1.base_query import FieldFilter
except Exception:
    firebase_auth = None
    firebase_firestore = None
    FieldFilter = None

api_bp = Blueprint('api', __name__, url_prefix='/api')


def require_firebase_token(f):
    """Decorator: validates Firebase ID token from Authorization header."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if firebase_auth is None:
            logger.error("Firebase auth module unavailable; rejecting request")
            return jsonify({'error': 'Service temporarily unavailable'}), 503
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid Authorization header'}), 401
        id_token = auth_header.split('Bearer ', 1)[1].strip()
        try:
            decoded = firebase_auth.verify_id_token(id_token)
        except Exception as exc:
            logger.warning("Token verification failed: %s", exc)
            return jsonify({'error': 'Invalid or expired token'}), 401
        # Attach verified uid to request context
        request.verified_uid = decoded['uid']
        return f(*args, **kwargs)
    return decorated


@api_bp.route('/projection', methods=['GET'], strict_slashes=False)
def get_projection_missing_uid():
    """Return a helpful 400 when the uid is omitted from the URL."""
    return jsonify({'error': 'Missing uid in URL. Use /api/projection/<uid>'}), 400


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
    logger.info("get_projection called for uid=%s", uid)

    try:
        return _get_projection_inner(uid)
    except Exception as exc:
        logger.exception(
            "Unhandled exception in get_projection for uid=%s: %s", uid, exc
        )
        return jsonify({'error': 'Internal server error computing projection'}), 500


def _get_projection_inner(uid):
    """Core logic for get_projection, wrapped by the outer handler."""

    if request.verified_uid != uid:
        return jsonify({'error': 'Forbidden: uid mismatch'}), 403

    # ── Firestore client ───────────────────────────────────────────────────
    try:
        if firebase_firestore is None:
            raise RuntimeError("Firebase Firestore module not available")
        db = firebase_firestore.client()
    except Exception as exc:
        logger.error("Could not obtain Firestore client for uid=%s: %s", uid, exc)
        return jsonify({'error': 'Database unavailable. Please try again later.'}), 503

    user_ref = db.collection('users').document(uid)

    # ── 1. Starting balance (sum of all accounts) ──────────────────────────
    try:
        accounts_snap = user_ref.collection('accounts').get()
        starting_balance = sum(
            float(doc.to_dict().get('balance', 0) or 0)
            for doc in accounts_snap
        )
    except Exception as exc:
        logger.warning("Could not read accounts for uid=%s: %s", uid, exc)
        starting_balance = 0.0

    logger.debug("uid=%s starting_balance=%.2f", uid, starting_balance)

    # Allow client override (e.g. when no accounts exist yet)
    try:
        override = request.args.get('starting_balance')
        if override is not None:
            starting_balance = float(override)
    except (ValueError, TypeError):
        pass

    # ── 2. Monthly net (income − spending) from last 3 months ─────────────
    now = datetime.now(timezone.utc)
    # Subtract 3 months safely, rolling back the year if necessary
    back_month = now.month - 3
    if back_month <= 0:
        back_month += 12
        back_year = now.year - 1
    else:
        back_year = now.year
    three_months_ago = datetime(back_year, back_month, 1, tzinfo=timezone.utc)

    total_income = 0.0
    total_spending = 0.0
    months_with_data = 1
    monthly_buckets: dict = {}

    try:
        if FieldFilter is not None:
            tx_query = user_ref.collection('transactions').where(
                filter=FieldFilter('date', '>=', three_months_ago)
            )
        else:
            # Fallback for older SDK versions without FieldFilter
            tx_query = user_ref.collection('transactions').where(
                'date', '>=', three_months_ago
            )
        tx_snap = tx_query.get()

        for doc in tx_snap:
            tx = doc.to_dict()
            amount = abs(float(tx.get('amount', 0) or 0))
            date = tx.get('date')
            if date is None:
                continue
            # Firestore DatetimeWithNanoseconds / google.cloud.firestore_v1.base_document
            # has a .date() method (not .todate()). Handle both Firestore timestamps and
            # plain datetime objects.
            if hasattr(date, 'to_datetime'):
                date = date.to_datetime()
            elif hasattr(date, 'timestamp'):
                # Firestore timestamp — call .datetime property or astimezone
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

    except Exception as exc:
        logger.warning("Could not compute monthly net for uid=%s: %s", uid, exc)
        monthly_net = 0.0

    logger.debug(
        "uid=%s monthly_net=%.2f (income=%.2f spending=%.2f months=%d)",
        uid,
        monthly_net,
        total_income,
        total_spending,
        months_with_data,
    )

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

    def _safe(val):
        """Replace NaN/Infinity with None so the JSON is always valid."""
        if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
            return None
        return val

    safe_balances = [_safe(b) for b in balances]

    logger.info(
        "get_projection success uid=%s starting=%.2f monthly_net=%.2f",
        uid,
        starting_balance,
        monthly_net,
    )

    return jsonify({
        'uid': uid,
        'starting_balance': _safe(round(starting_balance, 2)),
        'monthly_net': _safe(round(monthly_net, 2)),
        'balance_12m': safe_balances[11] if len(safe_balances) >= 12 else None,
        'balance_24m': safe_balances[23] if len(safe_balances) >= 24 else None,
        'balance_36m': safe_balances[35] if len(safe_balances) >= 36 else None,
        'labels': labels,
        'balances': safe_balances,
    })
