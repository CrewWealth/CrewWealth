from flask import Blueprint, jsonify, request
import requests
from datetime import datetime

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
        
        # Valuta beperken tot specifieke doelen
        target_currencies = {
            'EUR': 1.0,  # Basismunt
            'USD': data['rates'].get('USD'),
            'IDR': data['rates'].get('IDR'),
            'THB': data['rates'].get('THB'),
            'PHP': data['rates'].get('PHP'),
            'GBP': data['rates'].get('GBP'),
        }
        
        # JSON-response zonder HTML of templates
        return jsonify({
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'base': base_currency,
            'rates': target_currencies
        })
    
    except requests.exceptions.RequestException as req_err:
        return jsonify({
            'success': False,
            'error': f'API error: {req_err}'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500