"""
test_currency.py — Tests for Day 1 multi-currency scaffolding.

Covers:
- config/currencies.py: SUPPORTED_CURRENCIES list, DEFAULT_BASE_CURRENCY,
  CURRENCY_META, is_supported_currency()
- app/models/user.py: field-name constants re-exported from config.currencies
- app/routes/currency.py: /api/currencies endpoint returns correct structure
"""

import unittest


class TestSupportedCurrencies(unittest.TestCase):
    """Tests for config.currencies module."""

    def setUp(self):
        from config.currencies import (
            SUPPORTED_CURRENCIES,
            DEFAULT_BASE_CURRENCY,
            CURRENCY_META,
            is_supported_currency,
        )
        self.SUPPORTED_CURRENCIES = SUPPORTED_CURRENCIES
        self.DEFAULT_BASE_CURRENCY = DEFAULT_BASE_CURRENCY
        self.CURRENCY_META = CURRENCY_META
        self.is_supported_currency = is_supported_currency

    def test_supported_currencies_are_five(self):
        self.assertEqual(len(self.SUPPORTED_CURRENCIES), 5)

    def test_supported_currencies_exact_set(self):
        self.assertEqual(
            set(self.SUPPORTED_CURRENCIES),
            {'EUR', 'USD', 'GBP', 'PHP', 'IDR'},
        )

    def test_all_codes_are_uppercase_strings(self):
        for code in self.SUPPORTED_CURRENCIES:
            self.assertIsInstance(code, str)
            self.assertEqual(code, code.upper())

    def test_default_base_currency_is_eur(self):
        self.assertEqual(self.DEFAULT_BASE_CURRENCY, 'EUR')

    def test_default_base_currency_in_supported(self):
        self.assertIn(self.DEFAULT_BASE_CURRENCY, self.SUPPORTED_CURRENCIES)

    def test_currency_meta_covers_all_supported(self):
        for code in self.SUPPORTED_CURRENCIES:
            self.assertIn(code, self.CURRENCY_META, f"CURRENCY_META missing '{code}'")

    def test_currency_meta_fields(self):
        for code, meta in self.CURRENCY_META.items():
            self.assertIn('symbol', meta, f"'{code}' meta missing 'symbol'")
            self.assertIn('decimals', meta, f"'{code}' meta missing 'decimals'")
            self.assertIn('locale', meta, f"'{code}' meta missing 'locale'")
            self.assertIsInstance(meta['decimals'], int)

    def test_idr_has_zero_decimals(self):
        self.assertEqual(self.CURRENCY_META['IDR']['decimals'], 0)

    def test_is_supported_currency_true_for_valid(self):
        for code in self.SUPPORTED_CURRENCIES:
            self.assertTrue(self.is_supported_currency(code), f"Expected True for '{code}'")

    def test_is_supported_currency_false_for_invalid(self):
        for code in ['INR', 'NOK', 'SGD', 'AUD', 'JPY', 'CAD', 'THB', '', 'eur', 'usd']:
            self.assertFalse(self.is_supported_currency(code), f"Expected False for '{code}'")

    def test_is_supported_currency_false_for_non_string(self):
        self.assertFalse(self.is_supported_currency(None))
        self.assertFalse(self.is_supported_currency(123))
        self.assertFalse(self.is_supported_currency(['EUR']))


class TestUserModelConstants(unittest.TestCase):
    """Tests for field-name constants in app.models.user."""

    def test_field_constants_are_strings(self):
        from app.models.user import (
            FIELD_BASE_CURRENCY,
            FIELD_ACCOUNT_CURRENCY,
            FIELD_TX_CURRENCY,
        )
        self.assertEqual(FIELD_BASE_CURRENCY, 'baseCurrency')
        self.assertEqual(FIELD_ACCOUNT_CURRENCY, 'currency')
        self.assertEqual(FIELD_TX_CURRENCY, 'currency')

    def test_model_re_exports_currencies(self):
        from app.models.user import (
            SUPPORTED_CURRENCIES,
            DEFAULT_BASE_CURRENCY,
            is_supported_currency,
        )
        self.assertIsInstance(SUPPORTED_CURRENCIES, list)
        self.assertIsInstance(DEFAULT_BASE_CURRENCY, str)
        self.assertTrue(callable(is_supported_currency))


class TestCurrencyEndpoints(unittest.TestCase):
    """Tests for /api/currencies endpoint."""

    def setUp(self):
        from flask import Flask
        from app.routes.currency import currency_bp

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(currency_bp)
        self.client = app.test_client()

    def test_list_currencies_returns_200(self):
        resp = self.client.get('/api/currencies')
        self.assertEqual(resp.status_code, 200)

    def test_list_currencies_supported_field(self):
        resp = self.client.get('/api/currencies')
        data = resp.get_json()
        self.assertIn('supported', data)
        self.assertEqual(set(data['supported']), {'EUR', 'USD', 'GBP', 'PHP', 'IDR'})

    def test_list_currencies_default_field(self):
        resp = self.client.get('/api/currencies')
        data = resp.get_json()
        self.assertEqual(data.get('default'), 'EUR')

    def test_list_currencies_meta_field(self):
        resp = self.client.get('/api/currencies')
        data = resp.get_json()
        self.assertIn('meta', data)
        self.assertIn('EUR', data['meta'])

    def test_exchange_rates_rejects_unsupported_base(self):
        resp = self.client.get('/api/exchange-rates?base=INR')
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertFalse(data.get('success'))

    def test_fx_rates_placeholder_get(self):
        resp = self.client.get('/api/fx-rates/test_uid_123')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data.get('uid'), 'test_uid_123')
        self.assertIn('fxRates', data)
        self.assertIsInstance(data['fxRates'], list)

    def test_fx_rates_placeholder_post_valid(self):
        resp = self.client.post(
            '/api/fx-rates/test_uid_123',
            json={'base': 'USD', 'quote': 'EUR', 'rate': 0.92},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data.get('base'), 'USD')
        self.assertEqual(data.get('quote'), 'EUR')
        self.assertAlmostEqual(data.get('rate'), 0.92)

    def test_fx_rates_placeholder_post_unsupported_currency(self):
        resp = self.client.post(
            '/api/fx-rates/test_uid_123',
            json={'base': 'INR', 'quote': 'EUR', 'rate': 0.012},
        )
        self.assertEqual(resp.status_code, 400)

    def test_fx_rates_placeholder_post_invalid_rate(self):
        resp = self.client.post(
            '/api/fx-rates/test_uid_123',
            json={'base': 'USD', 'quote': 'EUR', 'rate': -1},
        )
        self.assertEqual(resp.status_code, 400)


if __name__ == '__main__':
    unittest.main()
