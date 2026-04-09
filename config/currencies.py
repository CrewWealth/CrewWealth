"""
currencies.py — CrewWealth backend currency constants.

This is the single source-of-truth for supported currencies on the backend.
Frontend equivalent: app/static/js/currency.js → SUPPORTED_CURRENCIES
"""

# ISO 4217 codes supported in the CrewWealth MVP.
# Any currency code not in this list is rejected by the API with HTTP 400.
SUPPORTED_CURRENCIES = ['EUR', 'USD', 'GBP', 'PHP', 'IDR']

# Default base currency applied to new users when no preference is set.
DEFAULT_BASE_CURRENCY = 'EUR'

# Per-currency display metadata (symbol, decimal places).
# Used for formatting in API responses and validation messages.
CURRENCY_META = {
    'EUR': {'symbol': '€',  'decimals': 2, 'locale': 'nl-NL'},
    'USD': {'symbol': '$',  'decimals': 2, 'locale': 'en-US'},
    'GBP': {'symbol': '£',  'decimals': 2, 'locale': 'en-GB'},
    'PHP': {'symbol': '₱',  'decimals': 2, 'locale': 'fil-PH'},
    'IDR': {'symbol': 'Rp', 'decimals': 0, 'locale': 'id-ID'},
}


def is_supported_currency(code: str) -> bool:
    """Return True if *code* is a valid, supported ISO 4217 code."""
    return isinstance(code, str) and code in SUPPORTED_CURRENCIES
