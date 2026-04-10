from flask import Blueprint, jsonify, request
import requests
from datetime import datetime
from app.routes.api import SUPPORTED_CURRENCIES

currency_bp = Blueprint('currency', __name__, url_prefix='/api')

@currency_bp.route('/exchange-rates')
def get_exchange_rates():
    """Fetch current exchange rates and return JSON"""
    base_currency = request.args.get('base', 'EUR').upper()  # Standaard naar 'EUR' voor de basis
    try:
        # Wisselkoersen ophalen
        response = requests.get(f'https://api.exchangerate-api.com/v4/latest/{base_currency}', timeout=5)
        response.raise_for_status()  # Controle op HTTP-statuscode
        data = response.json()
        
        # Valuta beperken tot de ondersteunde set (SUPPORTED_CURRENCIES).
        # Currencies whose rate is not provided by the API are omitted rather
        # than included as None, so callers can safely assume numeric values.
        target_currencies = {}
        for code in SUPPORTED_CURRENCIES:
            if code == base_currency:
                target_currencies[code] = 1.0
            else:
                rate = data['rates'].get(code)
                if rate is not None:
                    target_currencies[code] = rate
        
        # JSON-response zonder HTML of templates
        return jsonify({
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'base': base_currency,
            'rates': target_currencies
        })
    
    except requests.exceptions.RequestException:
        return jsonify({
            'success': False,
            'error': 'Failed to fetch exchange rates. Please try again later.'
        }), 500
    except Exception:
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred.'
        }), 500