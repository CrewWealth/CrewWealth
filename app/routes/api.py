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

    # ── 1. Starting balance (sum of off-budget accounts only) ──────────────
    off_budget_account_ids: set = set()
    starting_balance = 0.0

    try:
        accounts_snap = user_ref.collection('accounts').get()
        for doc in accounts_snap:
            data = doc.to_dict() or {}
            if data.get('offBudget'):
                starting_balance += float(data.get('balance', 0) or 0)
                off_budget_account_ids.add(doc.id)
    except Exception as exc:
        logger.warning("Could not read accounts for uid=%s: %s", uid, exc)

    logger.debug(
        "uid=%s off_budget starting_balance=%.2f accounts=%s",
        uid,
        starting_balance,
        off_budget_account_ids,
    )

    # ── 2. Check for manual monthly savings override in user settings ──────
    monthly_contribution = 0.0
    contribution_source = 'calculated'
    base_currency = 'EUR'  # default; overridden below if user has a preference

    try:
        from config.currencies import DEFAULT_BASE_CURRENCY, is_supported_currency
        user_doc = user_ref.get()
        if user_doc.exists:
            user_data = user_doc.to_dict() or {}
            # Read baseCurrency (new canonical field); fall back to settings.currency
            raw_currency = (
                user_data.get('baseCurrency')
                or (user_data.get('settings') or {}).get('currency')
                or DEFAULT_BASE_CURRENCY
            )
            if is_supported_currency(raw_currency):
                base_currency = raw_currency
            settings = user_data.get('settings') or {}
            override_val = settings.get('monthlySavings')
            if override_val is not None:
                manual_savings = float(override_val)
                monthly_contribution = manual_savings
                contribution_source = 'manual'
    except (TypeError, ValueError):
        pass
    except Exception as exc:
        logger.warning("Could not read user settings for uid=%s: %s", uid, exc)

    # ── 3. Auto-calculate monthly contribution from transfers ──────────────
    # Only computed when no manual override is in effect.
    if contribution_source == 'calculated':
        now = datetime.now(timezone.utc)
        back_month = now.month - 3
        if back_month <= 0:
            back_month += 12
            back_year = now.year - 1
        else:
            back_year = now.year
        three_months_ago = datetime(back_year, back_month, 1, tzinfo=timezone.utc)

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
                tx = doc.to_dict() or {}
                if tx.get('type') != 'transfer':
                    continue

                amount = abs(float(tx.get('amount', 0) or 0))
                date = tx.get('date')
                if date is None:
                    continue

                if hasattr(date, 'to_datetime'):
                    date = date.to_datetime()
                elif hasattr(date, 'timestamp'):
                    try:
                        date = date.astimezone(timezone.utc)
                    except Exception:
                        pass

                month_key = (
                    f"{date.year}-{date.month:02d}"
                    if hasattr(date, 'year')
                    else None
                )

                from_account_id = tx.get('accountId', '')
                to_account_id = tx.get('toAccountId', '')

                # Net flow INTO off-budget accounts
                net_delta = 0.0
                if to_account_id in off_budget_account_ids:
                    net_delta += amount
                if from_account_id in off_budget_account_ids:
                    net_delta -= amount

                if month_key is not None and net_delta != 0.0:
                    monthly_buckets.setdefault(month_key, 0.0)
                    monthly_buckets[month_key] += net_delta

            months_with_data = len(monthly_buckets) or 1
            monthly_contribution = sum(monthly_buckets.values()) / months_with_data

        except Exception as exc:
            logger.warning(
                "Could not compute monthly contribution for uid=%s: %s", uid, exc
            )
            monthly_contribution = 0.0

    logger.debug(
        "uid=%s monthly_contribution=%.2f source=%s",
        uid,
        monthly_contribution,
        contribution_source,
    )

    # ── 4. Build 36-month projection (simple linear, no interest) ──────────
    now = datetime.now(timezone.utc)
    labels = []
    balances = []

    for i in range(36):
        target_month = now.month + i
        target_year = now.year + (target_month - 1) // 12
        target_month = (target_month - 1) % 12 + 1
        label = datetime(target_year, target_month, 1).strftime('%b %Y')
        balance = round(starting_balance + monthly_contribution * (i + 1), 2)
        labels.append(label)
        balances.append(balance)

    def _safe(val):
        """Replace NaN/Infinity with None so the JSON is always valid."""
        if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
            return None
        return val

    safe_balances = [_safe(b) for b in balances]

    logger.info(
        "get_projection success uid=%s starting=%.2f monthly_contribution=%.2f source=%s",
        uid,
        starting_balance,
        monthly_contribution,
        contribution_source,
    )

    return jsonify({
        'uid': uid,
        'baseCurrency': base_currency,
        'starting_balance': _safe(round(starting_balance, 2)),
        'monthly_contribution': _safe(round(monthly_contribution, 2)),
        'contribution_source': contribution_source,
        'balance_12m': safe_balances[11] if len(safe_balances) >= 12 else None,
        'balance_24m': safe_balances[23] if len(safe_balances) >= 24 else None,
        'balance_36m': safe_balances[35] if len(safe_balances) >= 36 else None,
        'labels': labels,
        'balances': safe_balances,
    })
