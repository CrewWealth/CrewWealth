import logging
from flask import Blueprint, jsonify, request
import requests
from datetime import datetime

from config.currencies import SUPPORTED_CURRENCIES, DEFAULT_BASE_CURRENCY, is_supported_currency

logger = logging.getLogger(__name__)

currency_bp = Blueprint('currency', __name__, url_prefix='/api')


@currency_bp.route('/currencies')
def list_currencies():
    """Return the list of supported ISO 4217 currency codes."""
    from config.currencies import CURRENCY_META
    return jsonify({
        'supported': SUPPORTED_CURRENCIES,
        'default': DEFAULT_BASE_CURRENCY,
        'meta': CURRENCY_META,
    })


@currency_bp.route('/exchange-rates')
def get_exchange_rates():
    """Fetch current exchange rates for the supported currencies and return JSON.

    Query params:
      base (str, optional): Base currency code. Must be one of SUPPORTED_CURRENCIES.
                            Defaults to DEFAULT_BASE_CURRENCY ('EUR').
    """
    base_currency = request.args.get('base', DEFAULT_BASE_CURRENCY).upper()

    if not is_supported_currency(base_currency):
        return jsonify({
            'success': False,
            'error': f"Unsupported base currency '{base_currency}'. "
                     f"Supported: {', '.join(SUPPORTED_CURRENCIES)}",
        }), 400

    try:
        response = requests.get(
            f'https://api.exchangerate-api.com/v4/latest/{base_currency}',
            timeout=5,
        )
        response.raise_for_status()
        data = response.json()

        # Only return rates for the supported currencies
        target_rates = {
            code: data['rates'].get(code)
            for code in SUPPORTED_CURRENCIES
        }

        return jsonify({
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'base': base_currency,
            'rates': target_rates,
            'source': 'external',
        })

    except requests.exceptions.RequestException as exc:
        logger.warning("External exchange-rate fetch failed: %s", exc)
        return jsonify({
            'success': False,
            'error': 'Failed to fetch exchange rates. Please try again later.',
        }), 500
    except Exception as exc:
        logger.exception("Unexpected error in get_exchange_rates: %s", exc)
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred.',
        }), 500


# ── Manual FX rates placeholder (Day 4: full CRUD) ────────────────────────────
# For the MVP, users manage exchange rates manually in Settings.
# These endpoints are scaffolded here; full Firestore CRUD will be wired in Day 4.

@currency_bp.route('/fx-rates/<uid>', methods=['GET'])
def get_manual_fx_rates(uid):
    """
    [Placeholder – Day 4] Return all manual FX rates stored for a user.

    Expected Firestore structure:
      users/{uid}/fxRates/{rateId}
        base      : str   – from-currency ISO 4217
        quote     : str   – to-currency ISO 4217
        rate      : float – 1 unit of base = rate units of quote
        updatedAt : Timestamp
        source    : "manual"
    """
    # TODO (Day 4): read from Firestore users/{uid}/fxRates
    return jsonify({
        'uid': uid,
        'fxRates': [],
        'note': 'Manual FX rate management coming in Day 4.',
    }), 200


@currency_bp.route('/fx-rates/<uid>', methods=['POST'])
def set_manual_fx_rate(uid):
    """
    [Placeholder – Day 4] Create or update a manual FX rate for a user.

    Expected JSON body:
      { "base": "USD", "quote": "EUR", "rate": 0.92 }
    """
    body = request.get_json(silent=True) or {}
    base = (body.get('base') or '').upper()
    quote = (body.get('quote') or '').upper()

    if not is_supported_currency(base) or not is_supported_currency(quote):
        return jsonify({
            'error': f"Both base and quote must be supported currencies: {', '.join(SUPPORTED_CURRENCIES)}",
        }), 400

    try:
        rate = float(body.get('rate', 0))
        if rate <= 0:
            raise ValueError("rate must be positive")
    except (TypeError, ValueError):
        return jsonify({'error': "Field 'rate' must be a positive number."}), 400

    # TODO (Day 4): persist to Firestore users/{uid}/fxRates
    return jsonify({
        'uid': uid,
        'base': base,
        'quote': quote,
        'rate': rate,
        'source': 'manual',
        'note': 'Persistence not yet wired (Day 4).',
    }), 200