import unittest
from unittest.mock import MagicMock, patch


def _make_app():
    from flask import Flask
    from app.routes.main import main_bp

    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(main_bp)
    return app


class TestWhatsappBalance(unittest.TestCase):
    @patch('app.routes.main.firestore.client')
    def test_balance_comes_from_firestore_accounts(self, mock_client):
        app = _make_app()

        user_doc = MagicMock()
        user_doc.to_dict.return_value = {'baseCurrency': 'USD'}
        account_a = MagicMock()
        account_a.to_dict.return_value = {'balance': 100}
        account_b = MagicMock()
        account_b.to_dict.return_value = {'balance': 25.5}
        user_doc.reference.collection.return_value.get.return_value = [account_a, account_b]

        users_ref = MagicMock()
        users_ref.where.return_value.limit.return_value.get.return_value = [user_doc]
        mock_client.return_value.collection.return_value = users_ref

        with app.test_client() as client:
            response = client.post('/whatsapp', data={'Body': 'balance', 'From': 'whatsapp:+123'})

        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('125.50 USD', body)
        self.assertNotIn('1,234.56', body)

    @patch('app.routes.main.firestore.client')
    def test_balance_requires_linked_account(self, mock_client):
        app = _make_app()

        users_ref = MagicMock()
        users_ref.where.return_value.limit.return_value.get.return_value = []
        mock_client.return_value.collection.return_value = users_ref

        with app.test_client() as client:
            response = client.post('/whatsapp', data={'Body': 'balance', 'From': 'whatsapp:+999'})

        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('No linked account found', body)


if __name__ == '__main__':
    unittest.main()
