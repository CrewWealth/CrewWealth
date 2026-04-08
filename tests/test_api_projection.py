"""
Regression tests for the /api/projection endpoint.

Smoke-tests that guard against regressions such as the
'CollectionReference has no attribute doc' crash that caused production 500s
because the Python Firestore client requires .document() not .doc().
"""

import unittest
from unittest.mock import MagicMock, patch


def _make_app():
    """Create a minimal Flask test app with the api blueprint registered."""
    from flask import Flask
    from app.routes.api import api_bp

    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(api_bp)
    return app


class TestProjectionFirestoreMethod(unittest.TestCase):
    """Verify that the projection inner function uses .document(), not .doc()."""

    def test_no_doc_attribute_used(self):
        """
        The Python Firestore CollectionReference has .document() but NOT .doc().
        This test simulates that restriction and confirms the endpoint no longer
        raises AttributeError.
        """
        import app.routes.api as api_module

        uid = 'testuid123'

        # Build a mock CollectionReference that ONLY exposes .document()
        # (mirrors real google-cloud-firestore behaviour — no .doc() method)
        mock_doc_ref = MagicMock()
        mock_doc_ref.collection.return_value.get.return_value = []

        mock_collection = MagicMock(spec=[])  # spec=[] means no attributes by default
        # Explicitly add .document() but NOT .doc()
        mock_collection.document = MagicMock(return_value=mock_doc_ref)

        mock_db = MagicMock()
        mock_db.collection.return_value = mock_collection

        mock_firestore = MagicMock()
        mock_firestore.client.return_value = mock_db

        # Patch firebase modules inside the api module
        with patch.object(api_module, 'firebase_firestore', mock_firestore), \
             patch.object(api_module, 'FieldFilter', None):

            flask_app = _make_app()

            with flask_app.test_request_context(f'/api/projection/{uid}'):
                from flask import request as flask_request
                flask_request.verified_uid = uid
                flask_request.args = {}

                # This must NOT raise AttributeError
                response = api_module._get_projection_inner(uid)

        # Verify .document() was called with the correct uid (at least once)
        mock_collection.document.assert_called_with(uid)
        self.assertGreaterEqual(mock_collection.document.call_count, 1)
        # Confirm .doc() was never invoked (it does not exist on a real CollectionReference)
        self.assertFalse(hasattr(mock_collection, 'doc'),
                         "CollectionReference mock should not have .doc() — "
                         "if this assertion fails the fix was reverted")


class TestProjectionMissingToken(unittest.TestCase):
    """Verify that missing Authorization headers return 401 JSON, not 500."""

    def test_missing_auth_header_returns_401(self):
        flask_app = _make_app()
        client = flask_app.test_client()

        response = client.get('/api/projection/someuid')

        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertIn('error', data)

    def test_malformed_auth_header_returns_401(self):
        flask_app = _make_app()
        client = flask_app.test_client()

        response = client.get(
            '/api/projection/someuid',
            headers={'Authorization': 'NotBearer token'}
        )

        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertIn('error', data)


class TestProjectionMissingUid(unittest.TestCase):
    """Verify that omitting the uid in the URL returns 400 JSON."""

    def test_missing_uid_returns_400(self):
        flask_app = _make_app()
        client = flask_app.test_client()

        response = client.get('/api/projection')

        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('error', data)


if __name__ == '__main__':
    unittest.main()
