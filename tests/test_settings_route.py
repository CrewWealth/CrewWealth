"""
Regression test for the /settings route.

Guards against the bug where settings.html used a different Firebase project
(crewwealth-6af07) than the rest of the app (crewwealth-cbe02), causing
authenticated users to be redirected to /login when visiting /settings.

Verifies:
  - GET /settings returns HTTP 200 (not a redirect)
  - The page contains the correct Firebase project ID (crewwealth-cbe02)
  - The page does NOT contain the stale Firebase project ID (crewwealth-6af07)
  - The page contains the supported currency options (EUR, USD, GBP, PHP, IDR)
  - The page saves baseCurrency (not only settings.currency)
"""

import os
import unittest
from flask import Flask


def _make_app():
    """Create a minimal Flask test app with the main blueprint registered."""
    from app.routes.main import main_bp

    # Resolve the templates folder relative to the repo root so that
    # render_template() can find settings.html regardless of the working dir.
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    templates_dir = os.path.join(repo_root, 'app', 'templates')

    app = Flask(__name__, template_folder=templates_dir)
    app.config['TESTING'] = True
    app.register_blueprint(main_bp)
    return app


class TestSettingsRoute(unittest.TestCase):
    """Smoke tests for the /settings page route."""

    def setUp(self):
        self.app = _make_app()
        self.client = self.app.test_client()

    def test_settings_returns_200(self):
        """GET /settings must return 200, not a redirect to /login."""
        response = self.client.get('/settings')
        self.assertEqual(
            response.status_code,
            200,
            f"Expected 200 but got {response.status_code}. "
            "Settings page must not redirect HTTP requests "
            "(auth guard is handled client-side via Firebase).",
        )

    def test_settings_uses_correct_firebase_project(self):
        """settings.html must reference the active Firebase project (crewwealth-cbe02)."""
        response = self.client.get('/settings')
        html = response.data.decode('utf-8')
        self.assertIn(
            'crewwealth-cbe02',
            html,
            "settings.html must use Firebase project crewwealth-cbe02 (same as all other pages).",
        )

    def test_settings_does_not_use_old_firebase_project(self):
        """settings.html must NOT reference the stale Firebase project (crewwealth-6af07)."""
        response = self.client.get('/settings')
        html = response.data.decode('utf-8')
        self.assertNotIn(
            'crewwealth-6af07',
            html,
            "settings.html still references the old Firebase project crewwealth-6af07. "
            "This causes authenticated users to be redirected to /login.",
        )

    def test_settings_contains_supported_currencies(self):
        """settings.html must expose all five supported currency options."""
        response = self.client.get('/settings')
        html = response.data.decode('utf-8')
        for code in ('EUR', 'USD', 'GBP', 'PHP', 'IDR'):
            self.assertIn(
                f'value="{code}"',
                html,
                f"Currency option '{code}' is missing from the settings page.",
            )

    def test_settings_saves_base_currency_field(self):
        """settings.html script must write to baseCurrency (not only settings.currency)."""
        response = self.client.get('/settings')
        html = response.data.decode('utf-8')
        self.assertIn(
            'baseCurrency',
            html,
            "saveCurrency() must update the baseCurrency field so dashboard totals "
            "reflect the user's chosen currency.",
        )


if __name__ == '__main__':
    unittest.main()
