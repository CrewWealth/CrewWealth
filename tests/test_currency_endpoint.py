import unittest
from unittest.mock import MagicMock, patch


def _make_app():
    from flask import Flask
    from app.routes.currency import currency_bp

    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(currency_bp)
    return app


class TestExchangeRatesEndpoint(unittest.TestCase):
    def test_exchange_rates_includes_source_and_base(self):
        app = _make_app()
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            'rates': {'EUR': 1.0, 'USD': 1.1, 'GBP': 0.9, 'PHP': 60.0, 'IDR': 17000.0},
            'time_last_update_unix': 1234567890
        }

        with patch('app.routes.currency.requests.get', return_value=mock_response) as mock_get:
            with app.test_client() as client:
                response = client.get('/api/exchange-rates?base=USD')

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload.get('success'))
        self.assertEqual(payload.get('base'), 'USD')
        self.assertEqual(payload.get('source'), 'open.er-api.com')
        self.assertIn('fetchedAt', payload)
        mock_get.assert_called_once()

    def test_exchange_rates_invalid_base_falls_back_to_eur(self):
        app = _make_app()
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {'rates': {'EUR': 1.0, 'USD': 1.1}}

        with patch('app.routes.currency.requests.get', return_value=mock_response) as mock_get:
            with app.test_client() as client:
                response = client.get('/api/exchange-rates?base=ABC')

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload.get('base'), 'EUR')
        called_url = mock_get.call_args[0][0]
        self.assertTrue(called_url.endswith('/EUR'))

    def test_exchange_rates_request_failure_returns_500(self):
        app = _make_app()
        with patch('app.routes.currency.requests.get', side_effect=Exception('boom')):
            with app.test_client() as client:
                response = client.get('/api/exchange-rates?base=EUR')

        self.assertEqual(response.status_code, 500)
        payload = response.get_json()
        self.assertFalse(payload.get('success'))


if __name__ == '__main__':
    unittest.main()
