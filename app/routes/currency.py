from flask import Blueprint, jsonify
import requests
from datetime import datetime

currency_bp = Blueprint('currency', __name__, url_prefix='/api')

@currency_bp.route('/exchange-rates')
def get_exchange_rates():
    """Fetch current exchange rates"""
    try:
        # Using exchangerate-api.com (free tier, no key needed)
        response = requests.get('https://api.exchangerate-api.com/v4/latest/EUR')
        data = response.json()
        
        # Extract only the currencies we need
        rates = data.get('rates', {})
        target_currencies = {
            'EUR': 1.0,  # Base currency
            'USD': rates.get('USD'),
            'IDR': rates.get('IDR'),
            'THB': rates.get('THB'),
            'PHP': rates.get('PHP'),
            'GBP': rates.get('GBP'),
        }
        
        return jsonify({
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'base': 'EUR',
            'rates': target_currencies
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
