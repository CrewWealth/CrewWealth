import logging
import math
import requests
import csv
import io
from flask import Blueprint, jsonify, request, current_app
from functools import wraps
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Supported currencies (ISO 4217).  Keep in sync with frontend currency.js.
# ---------------------------------------------------------------------------
SUPPORTED_CURRENCIES = ['EUR', 'USD', 'GBP', 'PHP', 'IDR']
DEFAULT_CURRENCY = 'EUR'
DEFAULT_FX_FALLBACK_RATE = 1.0
PUBLIC_FX_API_BASE_URL = 'https://open.er-api.com/v6/latest/'
MAX_IMPORT_FILE_SIZE = 1_000_000

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

ALLOWED_SHARE_ROLES = {'owner', 'editor', 'viewer'}
ALLOWED_VISIBILITY_SCOPES = {'all', 'budget', 'goals', 'reports'}
DEFAULT_REPORT_PRESETS = {'monthly', 'quarterly', 'voyage'}


def _fx_pair_key(base_currency, quote_currency):
    return f"{(base_currency or '').upper()}_{(quote_currency or '').upper()}"


def _resolve_fx_rate(from_currency, to_currency, fx_rates):
    source = (from_currency or DEFAULT_CURRENCY).upper()
    target = (to_currency or DEFAULT_CURRENCY).upper()
    if source == target:
        return 1.0

    direct = fx_rates.get(_fx_pair_key(source, target))
    if isinstance(direct, (int, float)) and direct > 0:
        return float(direct)

    inverse = fx_rates.get(_fx_pair_key(target, source))
    if isinstance(inverse, (int, float)) and inverse > 0:
        return 1.0 / float(inverse)

    # Fallback: resolve through intermediate currencies when a complete direct
    # pair is missing (e.g. EUR->GBP via EUR->USD and USD->GBP).
    adjacency = {}
    for pair_key, raw_rate in (fx_rates or {}).items():
        try:
            rate = float(raw_rate)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(rate) or rate <= 0:
            continue
        parts = str(pair_key).split('_')
        if len(parts) != 2:
            continue
        base = (parts[0] or '').upper()
        quote = (parts[1] or '').upper()
        if not base or not quote:
            continue
        adjacency.setdefault(base, []).append((quote, rate))
        adjacency.setdefault(quote, []).append((base, 1.0 / rate))

    if source not in adjacency or target not in adjacency:
        return DEFAULT_FX_FALLBACK_RATE

    queue = [(source, 1.0)]
    visited = {source}

    while queue:
        currency, cumulative_rate = queue.pop(0)
        for next_currency, edge_rate in adjacency.get(currency, []):
            if next_currency in visited:
                continue
            next_rate = cumulative_rate * edge_rate
            if next_currency == target:
                return next_rate
            visited.add(next_currency)
            queue.append((next_currency, next_rate))

    return DEFAULT_FX_FALLBACK_RATE


def _load_public_fx_rates(base_currency):
    source = (base_currency or DEFAULT_CURRENCY).upper()
    rates = {}
    if source not in SUPPORTED_CURRENCIES:
        source = DEFAULT_CURRENCY

    if current_app and current_app.testing:
        return rates

    try:
        response = requests.get(
            f"{PUBLIC_FX_API_BASE_URL}{source}",
            timeout=3,
        )
        response.raise_for_status()
        payload = response.json() or {}
        api_rates = payload.get('rates') or {}
    except Exception as exc:
        logger.warning("Could not load public FX rates for %s: %s", source, exc)
        return rates

    for target in SUPPORTED_CURRENCIES:
        if target == source:
            rates[_fx_pair_key(source, target)] = 1.0
            continue
        try:
            rate = float(api_rates.get(target))
        except (TypeError, ValueError):
            continue
        if not math.isfinite(rate) or rate <= 0:
            continue
        rates[_fx_pair_key(source, target)] = rate
        rates[_fx_pair_key(target, source)] = 1.0 / rate

    return rates


def _to_float(value, default=0.0):
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return float(default)
    if not math.isfinite(numeric):
        return float(default)
    return numeric


def _build_projection_series(starting_balance, monthly_contribution, months):
    labels = []
    balances = []
    running = _to_float(starting_balance)
    monthly = _to_float(monthly_contribution)
    safe_months = max(1, min(int(months or 12), 120))
    for idx in range(safe_months):
        running += monthly
        labels.append(f"Month {idx + 1}")
        balances.append(round(running, 2))
    return labels, balances


def _infer_transaction_category(description, amount):
    normalized = (description or '').strip().lower()
    amount_num = _to_float(amount, 0.0)
    keyword_map = {
        'Housing': ['rent', 'mortgage', 'housing', 'apartment', 'utility'],
        'Transport': ['uber', 'taxi', 'fuel', 'train', 'flight', 'transport', 'parking'],
        'Groceries': ['supermarket', 'grocery', 'aldi', 'lidl', 'carrefour', 'tesco'],
        'Dining': ['restaurant', 'cafe', 'coffee', 'takeaway', 'food'],
        'Income': ['salary', 'payroll', 'wage', 'bonus', 'income'],
        'Travel': ['hotel', 'airbnb', 'booking', 'trip', 'voyage'],
        'Subscriptions': ['netflix', 'spotify', 'subscription', 'icloud', 'adobe'],
    }

    matches = []
    chosen_category = 'Uncategorized'
    for category, keywords in keyword_map.items():
        for keyword in keywords:
            if keyword in normalized:
                matches.append(keyword)
                chosen_category = category
    smart_tags = sorted(set(matches))
    if amount_num < 0:
        smart_tags.append('incoming')
    elif amount_num > 0:
        smart_tags.append('outgoing')

    if chosen_category == 'Uncategorized' and amount_num < 0:
        chosen_category = 'Income'
    confidence = 0.35 if chosen_category == 'Uncategorized' else min(0.95, 0.55 + (0.1 * len(matches)))
    return {
        'category': chosen_category,
        'confidence': round(confidence, 2),
        'smart_tags': smart_tags[:8],
        'matched_keywords': matches,
    }


def _parse_csv_transactions(content):
    rows = []
    reader = csv.DictReader(io.StringIO(content or ''))
    for row in reader:
        amount = _to_float(row.get('amount'), 0.0)
        currency = (row.get('currency') or DEFAULT_CURRENCY).upper()
        if currency not in SUPPORTED_CURRENCIES:
            currency = DEFAULT_CURRENCY
        rows.append({
            'date': (row.get('date') or '').strip(),
            'description': (row.get('description') or '').strip(),
            'amount': amount,
            'currency': currency,
            'category': (row.get('category') or '').strip() or None,
        })
    return rows


def _parse_mt940_transactions(content):
    transactions = []
    current = {}
    for raw_line in (content or '').splitlines():
        line = raw_line.strip()
        if line.startswith(':61:'):
            if current:
                transactions.append(current)
            payload = line[4:]
            date_raw = payload[:6]
            dc_mark = payload[6:7].upper()
            amount_chars = []
            for char in payload[7:]:
                if char.isdigit() or char == ',':
                    amount_chars.append(char)
                    continue
                if amount_chars:
                    break
            amount = _to_float(''.join(amount_chars).replace(',', '.'), 0.0)
            if dc_mark == 'D':
                amount = abs(amount)
            elif dc_mark == 'C':
                amount = -abs(amount)
            current = {
                'date': date_raw,
                'description': '',
                'amount': amount,
                'currency': DEFAULT_CURRENCY,
                'category': None,
            }
        elif line.startswith(':86:') and current:
            current['description'] = line[4:].strip()
    if current:
        transactions.append(current)
    return transactions


def _sanitize_csv_cell(value):
    text = str(value or '')
    if text.startswith(('=', '+', '-', '@')):
        return f"'{text}"
    return text


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


@api_bp.route('/currencies', methods=['GET'])
def get_currencies():
    """Return the list of supported currencies and the default base currency."""
    return jsonify({
        'supported': SUPPORTED_CURRENCIES,
        'default': DEFAULT_CURRENCY,
    })


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

    # ── 0. Read user document (base currency + settings) ──────────────────
    base_currency = DEFAULT_CURRENCY
    legacy_currency = DEFAULT_CURRENCY
    manual_monthly_savings = None
    manual_monthly_savings_currency = None
    monthly_contribution = 0.0
    contribution_source = 'calculated'

    try:
        user_doc = user_ref.get()
        if user_doc.exists:
            user_data = user_doc.to_dict() or {}
            # baseCurrency field takes precedence; fall back to settings.currency
            raw_bc = (
                user_data.get('baseCurrency')
                or (user_data.get('settings') or {}).get('currency')
                or DEFAULT_CURRENCY
            )
            if raw_bc in SUPPORTED_CURRENCIES:
                base_currency = raw_bc
            settings = user_data.get('settings') or {}
            raw_legacy_currency = (settings.get('currency') or base_currency).upper()
            if raw_legacy_currency in SUPPORTED_CURRENCIES:
                legacy_currency = raw_legacy_currency
            else:
                legacy_currency = base_currency
            override_val = settings.get('monthlySavings')
            if override_val is not None:
                try:
                    manual_monthly_savings = float(override_val)
                    manual_monthly_savings_currency = legacy_currency
                    contribution_source = 'manual'
                except (TypeError, ValueError):
                    pass
    except Exception as exc:
        logger.warning("Could not read user settings for uid=%s: %s", uid, exc)

    logger.debug("uid=%s base_currency=%s", uid, base_currency)

    # ── 0b. Read manual FX rates (users/{uid}/fxRates) ─────────────────────
    fx_rates = _load_public_fx_rates(base_currency)
    try:
        fx_snap = user_ref.collection('fxRates').get()
        for doc in fx_snap:
            data = doc.to_dict() or {}
            base = (data.get('base') or '').upper()
            quote = (data.get('quote') or '').upper()
            raw_rate = data.get('rate')
            try:
                rate = float(raw_rate)
            except (TypeError, ValueError):
                continue
            if (
                not base
                or not quote
                or not math.isfinite(rate)
                or rate <= 0
            ):
                continue
            # Manual rates always take precedence over auto-fetched public rates.
            fx_rates[_fx_pair_key(base, quote)] = rate
    except Exception as exc:
        logger.warning("Could not read fxRates for uid=%s: %s", uid, exc)

    if manual_monthly_savings is not None:
        source_currency = manual_monthly_savings_currency
        rate = _resolve_fx_rate(source_currency, base_currency, fx_rates)
        monthly_contribution = manual_monthly_savings * rate

    # ── 1. Starting balance (sum of off-budget accounts only) ──────────────
    off_budget_account_ids: set = set()
    account_currency_by_id: dict = {}
    missing_fx_pairs: set = set()
    starting_balance = 0.0

    try:
        accounts_snap = user_ref.collection('accounts').get()
        for doc in accounts_snap:
            data = doc.to_dict() or {}
            account_currency = (
                data.get('currency')
                or legacy_currency
            ).upper()
            account_currency_by_id[doc.id] = account_currency
            if data.get('offBudget'):
                raw_balance = float(data.get('balance', 0) or 0)
                rate = _resolve_fx_rate(account_currency, base_currency, fx_rates)
                if rate is None:
                    if account_currency != base_currency:
                        missing_fx_pairs.add(f"{account_currency}->{base_currency}")
                    continue
                starting_balance += raw_balance * rate
                off_budget_account_ids.add(doc.id)
    except Exception as exc:
        logger.warning("Could not read accounts for uid=%s: %s", uid, exc)

    logger.debug(
        "uid=%s off_budget starting_balance=%.2f accounts=%s",
        uid,
        starting_balance,
        off_budget_account_ids,
    )

    # ── 2. Auto-calculate monthly contribution from transfers ──────────────
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
                    to_currency = account_currency_by_id.get(to_account_id, base_currency)
                    rate = _resolve_fx_rate(to_currency, base_currency, fx_rates)
                    if rate is None:
                        if to_currency != base_currency:
                            missing_fx_pairs.add(f"{to_currency}->{base_currency}")
                        continue
                    net_delta += amount * rate
                if from_account_id in off_budget_account_ids:
                    from_currency = account_currency_by_id.get(from_account_id, base_currency)
                    rate = _resolve_fx_rate(from_currency, base_currency, fx_rates)
                    if rate is None:
                        if from_currency != base_currency:
                            missing_fx_pairs.add(f"{from_currency}->{base_currency}")
                        continue
                    net_delta -= amount * rate

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

    # ── 3. Build 36-month projection (simple linear, no interest) ──────────
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
        'base_currency': base_currency,
        'starting_balance': _safe(round(starting_balance, 2)),
        'monthly_contribution': _safe(round(monthly_contribution, 2)),
        'contribution_source': contribution_source,
        'missing_fx_pairs': sorted(missing_fx_pairs),
        'balance_12m': safe_balances[11] if len(safe_balances) >= 12 else None,
        'balance_24m': safe_balances[23] if len(safe_balances) >= 24 else None,
        'balance_36m': safe_balances[35] if len(safe_balances) >= 36 else None,
        'labels': labels,
        'balances': safe_balances,
    })


@api_bp.route('/day3/scenario/forecast', methods=['POST'])
def day3_forecast_scenario():
    payload = request.get_json(silent=True) or {}
    base_starting = _to_float(payload.get('starting_balance'), 0.0)
    base_monthly = _to_float(payload.get('monthly_contribution'), 0.0)
    months = max(1, min(int(payload.get('months') or 12), 120))
    scenario = payload.get('scenario') or {}

    income_delta = _to_float(scenario.get('income_delta'), 0.0)
    expense_delta = _to_float(scenario.get('expense_delta'), 0.0)
    one_off_adjustment = _to_float(scenario.get('one_off_adjustment'), 0.0)
    fx_shift_percent = _to_float(scenario.get('fx_shift_percent'), 0.0)
    fx_multiplier = 1.0 + (fx_shift_percent / 100.0)
    if not math.isfinite(fx_multiplier) or fx_multiplier <= 0:
        fx_multiplier = 1.0

    scenario_starting = (base_starting * fx_multiplier) + one_off_adjustment
    scenario_monthly = (base_monthly + income_delta - expense_delta) * fx_multiplier

    labels, baseline_balances = _build_projection_series(base_starting, base_monthly, months)
    _, scenario_balances = _build_projection_series(scenario_starting, scenario_monthly, months)
    delta_balances = [round(s - b, 2) for b, s in zip(baseline_balances, scenario_balances)]

    return jsonify({
        'temporary_preview': True,
        'labels': labels,
        'baseline': {
            'starting_balance': round(base_starting, 2),
            'monthly_contribution': round(base_monthly, 2),
            'balances': baseline_balances,
        },
        'scenario': {
            'starting_balance': round(scenario_starting, 2),
            'monthly_contribution': round(scenario_monthly, 2),
            'balances': scenario_balances,
            'delta_vs_baseline': delta_balances,
            'config': {
                'income_delta': round(income_delta, 2),
                'expense_delta': round(expense_delta, 2),
                'fx_shift_percent': round(fx_shift_percent, 2),
                'one_off_adjustment': round(one_off_adjustment, 2),
            },
        },
    })


@api_bp.route('/day3/transactions/categorize', methods=['POST'])
def day3_categorize_transaction():
    payload = request.get_json(silent=True) or {}
    description = str(payload.get('description') or '').strip()
    amount = _to_float(payload.get('amount'), 0.0)
    result = _infer_transaction_category(description, amount)
    result.update({
        'description': description,
        'amount': amount,
    })
    return jsonify(result)


@api_bp.route('/day3/sharing/validate', methods=['POST'])
def day3_validate_sharing():
    payload = request.get_json(silent=True) or {}
    invites = payload.get('invites') or []
    normalized = []
    for raw_invite in invites:
        invite = raw_invite or {}
        email = str(invite.get('email') or '').strip().lower()
        role = str(invite.get('role') or 'viewer').strip().lower()
        visibility = str(invite.get('visibility') or 'all').strip().lower()
        can_edit = bool(invite.get('canEdit', role in {'owner', 'editor'}))
        if '@' not in email:
            continue
        if role not in ALLOWED_SHARE_ROLES:
            role = 'viewer'
        if visibility not in ALLOWED_VISIBILITY_SCOPES:
            visibility = 'all'
        normalized.append({
            'email': email,
            'role': role,
            'visibility': visibility,
            'canEdit': can_edit and role != 'viewer',
        })
    return jsonify({
        'invites': normalized,
        'count': len(normalized),
    })


@api_bp.route('/day3/import/parse', methods=['POST'])
def day3_parse_import():
    payload = request.get_json(silent=True) or {}
    fmt = str(payload.get('format') or 'csv').strip().lower()
    content = str(payload.get('content') or '')

    if len(content) > MAX_IMPORT_FILE_SIZE:
        return jsonify({'error': 'Import file too large (max 1MB).'}), 400

    if fmt == 'csv':
        transactions = _parse_csv_transactions(content)
    elif fmt == 'mt940':
        transactions = _parse_mt940_transactions(content)
    else:
        return jsonify({'error': f'Unsupported import format: {fmt}'}), 400

    return jsonify({
        'format': fmt,
        'transactions': transactions[:1000],
        'count': len(transactions),
    })


@api_bp.route('/day3/export', methods=['POST'])
def day3_export_transactions():
    payload = request.get_json(silent=True) or {}
    export_format = str(payload.get('format') or 'csv').strip().lower()
    transactions = payload.get('transactions') or []

    normalized_rows = []
    for tx in transactions:
        row = tx or {}
        normalized_rows.append({
            'date': _sanitize_csv_cell(row.get('date') or ''),
            'description': _sanitize_csv_cell(row.get('description') or ''),
            'amount': _to_float(row.get('amount'), 0.0),
            'currency': str(row.get('currency') or DEFAULT_CURRENCY).upper(),
            'category': _sanitize_csv_cell(row.get('category') or ''),
            'tags': _sanitize_csv_cell(','.join([str(tag) for tag in (row.get('smart_tags') or [])][:8])),
        })

    if export_format == 'json':
        return jsonify({
            'format': 'json',
            'filename': 'crewwealth-export.json',
            'mimeType': 'application/json',
            'rows': normalized_rows,
            'count': len(normalized_rows),
        })

    if export_format != 'csv':
        return jsonify({'error': f'Unsupported export format: {export_format}'}), 400

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=['date', 'description', 'amount', 'currency', 'category', 'tags'])
    writer.writeheader()
    writer.writerows(normalized_rows)
    return jsonify({
        'format': 'csv',
        'filename': 'crewwealth-export.csv',
        'mimeType': 'text/csv',
        'content': output.getvalue(),
        'count': len(normalized_rows),
    })


@api_bp.route('/day3/presets/validate', methods=['POST'])
def day3_validate_presets():
    payload = request.get_json(silent=True) or {}
    favorite_currency = str(payload.get('favoriteCurrency') or DEFAULT_CURRENCY).upper()
    report_preset = str(payload.get('reportPreset') or 'monthly').lower()
    if favorite_currency not in SUPPORTED_CURRENCIES:
        favorite_currency = DEFAULT_CURRENCY
    if report_preset not in DEFAULT_REPORT_PRESETS:
        report_preset = 'monthly'
    return jsonify({
        'favoriteCurrency': favorite_currency,
        'reportPreset': report_preset,
    })
