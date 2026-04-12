"""
Regression tests for the /api/projection endpoint.

Smoke-tests that guard against regressions such as the
'CollectionReference has no attribute doc' crash that caused production 500s
because the Python Firestore client requires .document() not .doc().

Also covers the off-budget projection logic:
  - Starting balance is summed from off-budget accounts only.
  - Monthly contribution defaults to net transfers into off-budget accounts.
  - User can override monthly contribution via settings.monthlySavings.
  - Projection uses simple linear growth (no interest/return).
"""

import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch


def _make_app():
    """Create a minimal Flask test app with the api blueprint registered."""
    from flask import Flask
    from app.routes.api import api_bp

    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(api_bp)
    return app


def _make_mock_doc(data):
    """Return a MagicMock that behaves like a Firestore document snapshot."""
    doc = MagicMock()
    doc.to_dict.return_value = data
    doc.id = data.get('_id', 'doc_id')
    return doc


def _make_user_doc(settings=None):
    """Return a MagicMock that behaves like a Firestore user document."""
    user_doc = MagicMock()
    user_doc.exists = True
    user_doc.to_dict.return_value = {'settings': settings or {}}
    return user_doc


def _call_projection_inner(api_module, uid, mock_db, accounts, transactions,
                           user_settings=None, use_field_filter=False, fx_rates=None):
    """
    Helper: configure mocks and call _get_projection_inner.

    accounts: list of dicts with account data (use '_id' key for doc.id)
    transactions: list of dicts with transaction data
    user_settings: dict for settings field in user document, or None (no override)
    """
    account_docs = [_make_mock_doc(a) for a in accounts]
    tx_docs = [_make_mock_doc(t) for t in transactions]
    fx_rate_docs = [_make_mock_doc(r) for r in (fx_rates or [])]

    # user document
    if user_settings is not None:
        user_doc = _make_user_doc(user_settings)
    else:
        user_doc = MagicMock()
        user_doc.exists = False

    mock_doc_ref = MagicMock()
    # accounts collection returns account_docs directly
    # transactions collection supports .where().get()
    mock_accounts_col = MagicMock()
    mock_accounts_col.get.return_value = account_docs

    mock_tx_col = MagicMock()
    mock_tx_col.where.return_value.get.return_value = tx_docs
    # also support FieldFilter-style where(filter=...)
    mock_tx_col.where.return_value = MagicMock()
    mock_tx_col.where.return_value.get.return_value = tx_docs
    mock_fx_col = MagicMock()
    mock_fx_col.get.return_value = fx_rate_docs

    def _collection_side_effect(name):
        if name == 'accounts':
            return mock_accounts_col
        if name == 'transactions':
            return mock_tx_col
        if name == 'fxRates':
            return mock_fx_col
        return MagicMock()

    mock_doc_ref.collection.side_effect = _collection_side_effect
    mock_doc_ref.get.return_value = user_doc

    mock_collection = MagicMock(spec=[])
    mock_collection.document = MagicMock(return_value=mock_doc_ref)

    mock_db.collection.return_value = mock_collection

    flask_app = _make_app()
    field_filter = MagicMock() if use_field_filter else None

    with patch.object(api_module, 'FieldFilter', field_filter):
        with flask_app.test_request_context(f'/api/projection/{uid}'):
            from flask import request as flask_request
            flask_request.verified_uid = uid
            response = api_module._get_projection_inner(uid)

    return response


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
        # User document: no settings override
        mock_user_doc = MagicMock()
        mock_user_doc.exists = False
        mock_doc_ref.get.return_value = mock_user_doc

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

                # This must NOT raise AttributeError
                response = api_module._get_projection_inner(uid)

        # Verify .document() was called with the correct uid (at least once)
        mock_collection.document.assert_called_with(uid)
        self.assertGreaterEqual(mock_collection.document.call_count, 1)
        # Confirm .doc() was never invoked (it does not exist on a real CollectionReference)
        self.assertFalse(hasattr(mock_collection, 'doc'),
                         "CollectionReference mock should not have .doc() — "
                         "if this assertion fails the fix was reverted")


class TestProjectionOffBudgetAccounts(unittest.TestCase):
    """Verify that the projection uses off-budget accounts for starting balance."""

    def _setup_firestore(self, api_module, mock_db):
        mock_firestore = MagicMock()
        mock_firestore.client.return_value = mock_db
        self._patcher = patch.object(api_module, 'firebase_firestore', mock_firestore)
        self._patcher.start()

    def tearDown(self):
        if hasattr(self, '_patcher'):
            self._patcher.stop()

    def test_only_off_budget_accounts_in_starting_balance(self):
        """Starting balance uses only accounts with offBudget=True."""
        import app.routes.api as api_module

        uid = 'uid_offbudget'
        accounts = [
            {'_id': 'acc1', 'balance': 1000.0, 'offBudget': True},
            {'_id': 'acc2', 'balance': 500.0, 'offBudget': False},
            {'_id': 'acc3', 'balance': 250.0, 'offBudget': True},
        ]
        mock_db = MagicMock()
        self._setup_firestore(api_module, mock_db)

        response = _call_projection_inner(
            api_module, uid, mock_db, accounts=accounts, transactions=[]
        )
        data = response.get_json()

        # Only acc1 (1000) + acc3 (250) = 1250
        self.assertEqual(data['starting_balance'], 1250.0)

    def test_no_off_budget_accounts_gives_zero_starting_balance(self):
        """If no off-budget accounts exist, starting balance is 0."""
        import app.routes.api as api_module

        uid = 'uid_nooffbudget'
        accounts = [
            {'_id': 'acc1', 'balance': 999.0, 'offBudget': False},
        ]
        mock_db = MagicMock()
        self._setup_firestore(api_module, mock_db)

        response = _call_projection_inner(
            api_module, uid, mock_db, accounts=accounts, transactions=[]
        )
        data = response.get_json()

        self.assertEqual(data['starting_balance'], 0.0)

    def test_response_has_monthly_contribution_not_monthly_net(self):
        """Response must include monthly_contribution and contribution_source."""
        import app.routes.api as api_module

        uid = 'uid_fields'
        mock_db = MagicMock()
        self._setup_firestore(api_module, mock_db)

        response = _call_projection_inner(
            api_module, uid, mock_db, accounts=[], transactions=[]
        )
        data = response.get_json()

        self.assertIn('monthly_contribution', data)
        self.assertIn('contribution_source', data)
        self.assertNotIn('monthly_net', data)

    def test_off_budget_balance_converts_to_base_currency_with_fx_rate(self):
        """Off-budget balances are converted to base_currency using a valid FX rate."""
        import app.routes.api as api_module

        uid = 'uid_fx_convert'
        accounts = [{'_id': 'acc_eur', 'balance': 1200.0, 'offBudget': True, 'currency': 'EUR'}]
        fx_rates = [{'_id': 'r1', 'base': 'EUR', 'quote': 'PHP', 'rate': 62.0}]
        mock_db = MagicMock()
        self._setup_firestore(api_module, mock_db)

        response = _call_projection_inner(
            api_module,
            uid,
            mock_db,
            accounts=accounts,
            transactions=[],
            user_settings={'currency': 'PHP'},
            fx_rates=fx_rates,
        )
        data = response.get_json()

        self.assertEqual(data['base_currency'], 'PHP')
        self.assertEqual(data['starting_balance'], 74400.0)
        self.assertEqual(data.get('missing_fx_pairs'), [])

    def test_off_budget_balance_requires_fx_rate_when_currency_differs(self):
        """Missing FX rates exclude unmatched balances and return missing pair list."""
        import app.routes.api as api_module

        uid = 'uid_fx_missing'
        accounts = [{'_id': 'acc_eur', 'balance': 1200.0, 'offBudget': True, 'currency': 'EUR'}]
        mock_db = MagicMock()
        self._setup_firestore(api_module, mock_db)

        response = _call_projection_inner(
            api_module,
            uid,
            mock_db,
            accounts=accounts,
            transactions=[],
            user_settings={'currency': 'PHP'},
            fx_rates=[],
        )
        data = response.get_json()

        self.assertEqual(data['base_currency'], 'PHP')
        self.assertEqual(data['starting_balance'], 0.0)
        self.assertIn('EUR->PHP', data.get('missing_fx_pairs', []))


class TestProjectionManualSavingsOverride(unittest.TestCase):
    """Verify that settings.monthlySavings overrides the auto-calculated value."""

    def _setup_firestore(self, api_module, mock_db):
        mock_firestore = MagicMock()
        mock_firestore.client.return_value = mock_db
        self._patcher = patch.object(api_module, 'firebase_firestore', mock_firestore)
        self._patcher.start()

    def tearDown(self):
        if hasattr(self, '_patcher'):
            self._patcher.stop()

    def test_manual_savings_overrides_transfers(self):
        """When settings.monthlySavings is set, it is used instead of transfer calc."""
        import app.routes.api as api_module

        uid = 'uid_manual'
        accounts = [{'_id': 'acc1', 'balance': 5000.0, 'offBudget': True}]
        # Transfer that would compute to 200/month — should be ignored
        now = datetime.now(timezone.utc)
        transactions = [{
            '_id': 'tx1',
            'type': 'transfer',
            'amount': 200.0,
            'accountId': 'budget_acc',
            'toAccountId': 'acc1',
            'date': datetime(now.year, now.month, 1, tzinfo=timezone.utc),
        }]
        mock_db = MagicMock()
        self._setup_firestore(api_module, mock_db)

        response = _call_projection_inner(
            api_module, uid, mock_db,
            accounts=accounts,
            transactions=transactions,
            user_settings={'monthlySavings': 750.0},
        )
        data = response.get_json()

        self.assertEqual(data['monthly_contribution'], 750.0)
        self.assertEqual(data['contribution_source'], 'manual')

    def test_no_manual_savings_uses_calculated_source(self):
        """When no settings.monthlySavings, contribution_source is 'calculated'."""
        import app.routes.api as api_module

        uid = 'uid_autocalc'
        mock_db = MagicMock()
        self._setup_firestore(api_module, mock_db)

        response = _call_projection_inner(
            api_module, uid, mock_db, accounts=[], transactions=[]
        )
        data = response.get_json()

        self.assertEqual(data['contribution_source'], 'calculated')


class TestProjectionTransferCalculation(unittest.TestCase):
    """Verify auto-calculated monthly contribution from net transfers."""

    def _setup_firestore(self, api_module, mock_db):
        mock_firestore = MagicMock()
        mock_firestore.client.return_value = mock_db
        self._patcher = patch.object(api_module, 'firebase_firestore', mock_firestore)
        self._patcher.start()

    def tearDown(self):
        if hasattr(self, '_patcher'):
            self._patcher.stop()

    def test_transfers_into_off_budget_are_positive(self):
        """Transfers from budget to off-budget accounts increase monthly contribution."""
        import app.routes.api as api_module

        uid = 'uid_transfer_in'
        accounts = [{'_id': 'savings', 'balance': 1000.0, 'offBudget': True}]
        now = datetime.now(timezone.utc)
        transactions = [{
            '_id': 'tx1',
            'type': 'transfer',
            'amount': 500.0,
            'accountId': 'checking',   # budget (not in off_budget_account_ids)
            'toAccountId': 'savings',  # off-budget
            'date': datetime(now.year, now.month, 1, tzinfo=timezone.utc),
        }]
        mock_db = MagicMock()
        self._setup_firestore(api_module, mock_db)

        response = _call_projection_inner(
            api_module, uid, mock_db, accounts=accounts, transactions=transactions
        )
        data = response.get_json()

        # Single month with a 500 transfer in → monthly_contribution = 500
        self.assertEqual(data['monthly_contribution'], 500.0)
        self.assertEqual(data['contribution_source'], 'calculated')

    def test_transfers_out_of_off_budget_are_negative(self):
        """Transfers from off-budget to budget accounts reduce monthly contribution."""
        import app.routes.api as api_module

        uid = 'uid_transfer_out'
        accounts = [{'_id': 'savings', 'balance': 2000.0, 'offBudget': True}]
        now = datetime.now(timezone.utc)
        transactions = [{
            '_id': 'tx1',
            'type': 'transfer',
            'amount': 300.0,
            'accountId': 'savings',   # off-budget
            'toAccountId': 'checking', # budget
            'date': datetime(now.year, now.month, 1, tzinfo=timezone.utc),
        }]
        mock_db = MagicMock()
        self._setup_firestore(api_module, mock_db)

        response = _call_projection_inner(
            api_module, uid, mock_db, accounts=accounts, transactions=transactions
        )
        data = response.get_json()

        self.assertEqual(data['monthly_contribution'], -300.0)

    def test_non_transfer_transactions_are_ignored(self):
        """salary/deposit/payment transactions do not affect monthly contribution."""
        import app.routes.api as api_module

        uid = 'uid_nontransfer'
        accounts = [{'_id': 'savings', 'balance': 1000.0, 'offBudget': True}]
        now = datetime.now(timezone.utc)
        transactions = [
            {
                '_id': 'tx1', 'type': 'salary', 'amount': 3000.0,
                'date': datetime(now.year, now.month, 1, tzinfo=timezone.utc),
            },
            {
                '_id': 'tx2', 'type': 'payment', 'amount': 500.0,
                'date': datetime(now.year, now.month, 1, tzinfo=timezone.utc),
            },
        ]
        mock_db = MagicMock()
        self._setup_firestore(api_module, mock_db)

        response = _call_projection_inner(
            api_module, uid, mock_db, accounts=accounts, transactions=transactions
        )
        data = response.get_json()

        self.assertEqual(data['monthly_contribution'], 0.0)

    def test_projection_is_simple_linear_no_interest(self):
        """Balances grow linearly: balance[i] = starting + contribution * (i+1)."""
        import app.routes.api as api_module

        uid = 'uid_linear'
        accounts = [{'_id': 'savings', 'balance': 1000.0, 'offBudget': True}]
        mock_db = MagicMock()
        self._setup_firestore(api_module, mock_db)

        # Use manual savings of exactly 100/month to make the math deterministic
        response = _call_projection_inner(
            api_module, uid, mock_db,
            accounts=accounts,
            transactions=[],
            user_settings={'monthlySavings': 100.0},
        )
        data = response.get_json()

        balances = data['balances']
        self.assertEqual(len(balances), 36)
        # Month 1: 1000 + 100*1 = 1100
        self.assertAlmostEqual(balances[0], 1100.0)
        # Month 12: 1000 + 100*12 = 2200
        self.assertAlmostEqual(balances[11], 2200.0)
        self.assertAlmostEqual(data['balance_12m'], 2200.0)
        # Month 36: 1000 + 100*36 = 4600
        self.assertAlmostEqual(balances[35], 4600.0)
        self.assertAlmostEqual(data['balance_36m'], 4600.0)


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


class TestProjectionDashboardReportsConsistency(unittest.TestCase):
    """
    Regression tests ensuring dashboard and reports pages consume the same
    API response schema.

    Root cause of the original bug: the dashboard read ``data.monthly_net``
    (always undefined/0) while the API returns ``monthly_contribution`` and
    the reports page resolved it with a proper fallback chain.

    These tests:
    1. Confirm the API never includes a ``monthly_net`` key in its response.
    2. Confirm the API always includes ``monthly_contribution``.
    3. Simulate the dashboard JS fallback logic against a mocked API response
       and verify it produces the same value as the reports page logic.
    """

    def _setup_firestore(self, api_module, mock_db):
        mock_firestore = MagicMock()
        mock_firestore.client.return_value = mock_db
        self._patcher = patch.object(api_module, 'firebase_firestore', mock_firestore)
        self._patcher.start()

    def tearDown(self):
        if hasattr(self, '_patcher'):
            self._patcher.stop()

    def test_api_returns_monthly_contribution_not_monthly_net(self):
        """API response must use monthly_contribution, never monthly_net."""
        import app.routes.api as api_module

        uid = 'uid_schema_check'
        mock_db = MagicMock()
        self._setup_firestore(api_module, mock_db)

        response = _call_projection_inner(
            api_module, uid, mock_db,
            accounts=[{'_id': 'acc1', 'balance': 1000.0, 'offBudget': True}],
            transactions=[],
            user_settings={'monthlySavings': 300.0},
        )
        data = response.get_json()

        # Field must exist under the correct camelCase-ish snake_case name
        self.assertIn('monthly_contribution', data,
                      "API must return 'monthly_contribution'")
        # Legacy field must NOT be present so we can detect accidental regressions
        self.assertNotIn('monthly_net', data,
                         "API must not return 'monthly_net' (legacy/wrong field)")

    def _simulate_dashboard_js_resolve(self, api_data):
        """
        Mirror the JS fallback chain used in loadDashboardProjection (fixed):
            data.monthly_contribution ?? data.monthlyContribution
            ?? data.monthly_net ?? data.netPerMonth
        The JS ``??`` operator only skips null/undefined, not 0 or falsy values,
        so we use explicit ``is None`` checks here to match that behaviour.
        Returns the resolved float or None.
        """
        for key in ('monthly_contribution', 'monthlyContribution', 'monthly_net', 'netPerMonth'):
            if key in api_data and api_data[key] is not None:
                try:
                    return float(api_data[key])
                except (TypeError, ValueError):
                    return None
        return None

    def _simulate_reports_js_resolve(self, api_data):
        """
        Mirror the JS fallback chain used in loadProjectionFromAPI (reports):
            data.monthly_contribution ?? data.monthlyContribution
            ?? data.monthly_net ?? data.netPerMonth
        Returns the resolved float or None.
        """
        return self._simulate_dashboard_js_resolve(api_data)

    def test_dashboard_and_reports_resolve_same_monthly_value(self):
        """
        Given a realistic API response, dashboard and reports JS logic must
        resolve to the same monthly contribution value.
        """
        import app.routes.api as api_module

        uid = 'uid_consistency'
        mock_db = MagicMock()
        self._setup_firestore(api_module, mock_db)

        accounts = [{'_id': 'acc1', 'balance': 5000.0, 'offBudget': True}]
        now = datetime.now(timezone.utc)
        transactions = [{
            '_id': 'tx1',
            'type': 'transfer',
            'amount': 400.0,
            'accountId': 'checking',
            'toAccountId': 'acc1',
            'date': datetime(now.year, now.month, 1, tzinfo=timezone.utc),
        }]

        response = _call_projection_inner(
            api_module, uid, mock_db,
            accounts=accounts,
            transactions=transactions,
        )
        data = response.get_json()

        dashboard_value = self._simulate_dashboard_js_resolve(data)
        reports_value = self._simulate_reports_js_resolve(data)

        self.assertIsNotNone(dashboard_value,
                             "Dashboard JS must resolve a non-None monthly value")
        self.assertIsNotNone(reports_value,
                             "Reports JS must resolve a non-None monthly value")
        self.assertEqual(dashboard_value, reports_value,
                         "Dashboard and reports must show the same Net/month value")

    def test_dashboard_net_month_matches_projection_balances(self):
        """
        The monthly_contribution in the API response must equal the delta
        between consecutive projected balances (i.e. balance[1] - balance[0]).
        """
        import app.routes.api as api_module

        uid = 'uid_delta_check'
        mock_db = MagicMock()
        self._setup_firestore(api_module, mock_db)

        response = _call_projection_inner(
            api_module, uid, mock_db,
            accounts=[{'_id': 'acc1', 'balance': 2000.0, 'offBudget': True}],
            transactions=[],
            user_settings={'monthlySavings': 250.0},
        )
        data = response.get_json()

        monthly = data['monthly_contribution']
        balances = data['balances']

        # The step between any two consecutive months must equal monthly_contribution
        self.assertAlmostEqual(balances[1] - balances[0], monthly,
                               places=2,
                               msg="Net/month must equal the per-month step in the projection")


# ---------------------------------------------------------------------------
# Day-1 multi-currency: SUPPORTED_CURRENCIES constant and base_currency field
# ---------------------------------------------------------------------------

class TestSupportedCurrencies(unittest.TestCase):
    """Tests for the SUPPORTED_CURRENCIES constant and DEFAULT_CURRENCY."""

    def test_supported_currencies_contains_required_codes(self):
        from app.routes.api import SUPPORTED_CURRENCIES
        for code in ('EUR', 'USD', 'GBP', 'PHP', 'IDR'):
            self.assertIn(code, SUPPORTED_CURRENCIES,
                          f"SUPPORTED_CURRENCIES must include {code}")

    def test_default_currency_is_eur(self):
        from app.routes.api import DEFAULT_CURRENCY
        self.assertEqual(DEFAULT_CURRENCY, 'EUR')

    def test_supported_currencies_are_uppercase_iso4217(self):
        from app.routes.api import SUPPORTED_CURRENCIES
        for code in SUPPORTED_CURRENCIES:
            self.assertEqual(code, code.upper(),
                             f"Currency code '{code}' must be uppercase")
            self.assertEqual(len(code), 3,
                             f"Currency code '{code}' must be 3 characters (ISO 4217)")


class TestProjectionBaseCurrency(unittest.TestCase):
    """Tests that the projection endpoint returns the user's base_currency."""

    def _setup_firestore(self, api_module, mock_db):
        """Patch firebase_firestore.client() on the given api_module."""
        mock_firestore = MagicMock()
        mock_firestore.client.return_value = mock_db
        api_module.firebase_firestore = mock_firestore

    def _call(self, uid, mock_db, accounts, transactions, user_data=None):
        import app.routes.api as api_module
        from flask import Flask
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(api_module.api_bp)

        account_docs = [_make_mock_doc(a) for a in accounts]
        tx_docs = [_make_mock_doc(t) for t in transactions]

        if user_data is not None:
            user_doc = MagicMock()
            user_doc.exists = True
            user_doc.to_dict.return_value = user_data
        else:
            user_doc = MagicMock()
            user_doc.exists = False

        mock_accounts_col = MagicMock()
        mock_accounts_col.get.return_value = account_docs
        mock_tx_col = MagicMock()
        mock_tx_col.where.return_value = MagicMock()
        mock_tx_col.where.return_value.get.return_value = tx_docs

        def _col(name):
            if name == 'accounts':
                return mock_accounts_col
            if name == 'transactions':
                return mock_tx_col
            return MagicMock()

        mock_doc_ref = MagicMock()
        mock_doc_ref.collection.side_effect = _col
        mock_doc_ref.get.return_value = user_doc

        mock_collection = MagicMock(spec=[])
        mock_collection.document = MagicMock(return_value=mock_doc_ref)
        mock_db.collection.return_value = mock_collection

        self._setup_firestore(api_module, mock_db)

        with app.test_request_context(f'/api/projection/{uid}'):
            from flask import request as flask_request
            flask_request.verified_uid = uid
            return api_module._get_projection_inner(uid)

    def test_projection_returns_base_currency_field(self):
        """Projection response must include 'base_currency'."""
        mock_db = MagicMock()
        response = self._call('uid_bc1', mock_db, [], [],
                              user_data={'baseCurrency': 'EUR', 'settings': {}})
        data = response.get_json()
        self.assertIn('base_currency', data,
                      "Projection response must include 'base_currency'")

    def test_base_currency_defaults_to_eur_when_not_set(self):
        """When user doc has no baseCurrency, response base_currency must be EUR."""
        mock_db = MagicMock()
        response = self._call('uid_bc2', mock_db, [], [], user_data=None)
        data = response.get_json()
        self.assertEqual(data.get('base_currency'), 'EUR')

    def test_base_currency_reads_baseCurrency_field(self):
        """baseCurrency field in user document takes effect in projection."""
        mock_db = MagicMock()
        response = self._call('uid_bc3', mock_db, [], [],
                              user_data={'baseCurrency': 'PHP', 'settings': {}})
        data = response.get_json()
        self.assertEqual(data.get('base_currency'), 'PHP')

    def test_base_currency_falls_back_to_settings_currency(self):
        """When baseCurrency is absent, settings.currency is used as fallback."""
        mock_db = MagicMock()
        response = self._call('uid_bc4', mock_db, [], [],
                              user_data={'settings': {'currency': 'GBP'}})
        data = response.get_json()
        self.assertEqual(data.get('base_currency'), 'GBP')

    def test_unsupported_base_currency_defaults_to_eur(self):
        """Unknown currency codes in baseCurrency must be ignored; default EUR used."""
        mock_db = MagicMock()
        response = self._call('uid_bc5', mock_db, [], [],
                              user_data={'baseCurrency': 'XYZ', 'settings': {}})
        data = response.get_json()
        self.assertEqual(data.get('base_currency'), 'EUR')


class TestCurrenciesEndpoint(unittest.TestCase):
    """Tests for the /api/currencies endpoint."""

    def _make_app(self):
        from flask import Flask
        from app.routes.api import api_bp
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(api_bp)
        return app

    def test_currencies_endpoint_returns_200(self):
        app = self._make_app()
        with app.test_client() as client:
            response = client.get('/api/currencies')
        self.assertEqual(response.status_code, 200)

    def test_currencies_endpoint_lists_supported(self):
        from app.routes.api import SUPPORTED_CURRENCIES
        app = self._make_app()
        with app.test_client() as client:
            response = client.get('/api/currencies')
        data = response.get_json()
        self.assertIn('supported', data)
        self.assertEqual(sorted(data['supported']), sorted(SUPPORTED_CURRENCIES))

    def test_currencies_endpoint_includes_default(self):
        app = self._make_app()
        with app.test_client() as client:
            response = client.get('/api/currencies')
        data = response.get_json()
        self.assertIn('default', data)
        self.assertEqual(data['default'], 'EUR')


if __name__ == '__main__':
    unittest.main()
