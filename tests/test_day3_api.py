import unittest


def _make_app():
    from flask import Flask
    from app.routes.api import api_bp

    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(api_bp)
    return app


class TestDay3Api(unittest.TestCase):
    def test_scenario_forecast_returns_temporary_preview(self):
        app = _make_app()
        with app.test_client() as client:
            response = client.post('/api/day3/scenario/forecast', json={
                'starting_balance': 1000,
                'monthly_contribution': 200,
                'months': 3,
                'scenario': {
                    'income_delta': 50,
                    'expense_delta': 10,
                    'fx_shift_percent': 5,
                    'one_off_adjustment': 100,
                },
            })

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload.get('temporary_preview'))
        self.assertEqual(len(payload.get('labels', [])), 3)
        self.assertEqual(len(payload.get('baseline', {}).get('balances', [])), 3)
        self.assertEqual(len(payload.get('scenario', {}).get('balances', [])), 3)

    def test_categorize_transaction_returns_tags(self):
        app = _make_app()
        with app.test_client() as client:
            response = client.post('/api/day3/transactions/categorize', json={
                'description': 'Uber airport ride',
                'amount': 42.75,
            })

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload.get('category'), 'Transport')
        self.assertIn('uber', payload.get('smart_tags', []))

    def test_sharing_validate_filters_invalid_invites(self):
        app = _make_app()
        with app.test_client() as client:
            response = client.post('/api/day3/sharing/validate', json={
                'invites': [
                    {'email': 'partner@example.com', 'role': 'editor', 'visibility': 'budget', 'canEdit': True},
                    {'email': 'invalid-email', 'role': 'admin', 'visibility': 'private', 'canEdit': True},
                ]
            })

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        invites = payload.get('invites', [])
        self.assertEqual(len(invites), 1)
        self.assertEqual(invites[0].get('role'), 'editor')
        self.assertEqual(invites[0].get('visibility'), 'budget')

    def test_import_parse_csv(self):
        app = _make_app()
        csv_content = "date,description,amount,currency,category\n2026-04-01,Coffee,3.5,EUR,Dining\n"
        with app.test_client() as client:
            response = client.post('/api/day3/import/parse', json={
                'format': 'csv',
                'content': csv_content,
            })

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload.get('count'), 1)
        tx = payload['transactions'][0]
        self.assertEqual(tx.get('description'), 'Coffee')
        self.assertEqual(tx.get('currency'), 'EUR')

    def test_import_parse_mt940(self):
        app = _make_app()
        mt940_content = ":61:260401D12,34NTRF\n:86:Groceries store\n"
        with app.test_client() as client:
            response = client.post('/api/day3/import/parse', json={
                'format': 'mt940',
                'content': mt940_content,
            })

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload.get('count'), 1)
        tx = payload['transactions'][0]
        self.assertEqual(tx.get('description'), 'Groceries store')
        self.assertAlmostEqual(tx.get('amount'), 12.34, places=2)

    def test_export_csv(self):
        app = _make_app()
        with app.test_client() as client:
            response = client.post('/api/day3/export', json={
                'format': 'csv',
                'transactions': [
                    {'date': '2026-04-01', 'description': 'Lunch', 'amount': 10, 'currency': 'EUR', 'category': 'Dining'}
                ],
            })

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload.get('format'), 'csv')
        self.assertIn('date,description,amount,currency,category,tags', payload.get('content', ''))

    def test_presets_validate_fallbacks(self):
        app = _make_app()
        with app.test_client() as client:
            response = client.post('/api/day3/presets/validate', json={
                'favoriteCurrency': 'abc',
                'reportPreset': 'yearly',
            })

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload.get('favoriteCurrency'), 'EUR')
        self.assertEqual(payload.get('reportPreset'), 'monthly')


if __name__ == '__main__':
    unittest.main()
