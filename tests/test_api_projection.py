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
                           user_settings=None, use_field_filter=False):
    """
    Helper: configure mocks and call _get_projection_inner.

    accounts: list of dicts with account data (use '_id' key for doc.id)
    transactions: list of dicts with transaction data
    user_settings: dict for settings field in user document, or None (no override)
    """
    account_docs = [_make_mock_doc(a) for a in accounts]
    tx_docs = [_make_mock_doc(t) for t in transactions]

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

    def _collection_side_effect(name):
        if name == 'accounts':
            return mock_accounts_col
        if name == 'transactions':
            return mock_tx_col
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


class TestDashboardProjectionFieldMapping(unittest.TestCase):
    """
    Regression tests that guard against the dashboard 'Net / month = €0.00' bug.

    Root cause: index.html was reading data.monthly_net (undefined) instead of
    data.monthly_contribution (the actual field returned by the API).  These
    tests verify that the API always returns monthly_contribution so the
    dashboard field mapping is stable.
    """

    def _setup_firestore(self, api_module, mock_db):
        mock_firestore = MagicMock()
        mock_firestore.client.return_value = mock_db
        self._patcher = patch.object(api_module, 'firebase_firestore', mock_firestore)
        self._patcher.start()

    def tearDown(self):
        if hasattr(self, '_patcher'):
            self._patcher.stop()

    def test_monthly_contribution_present_and_numeric(self):
        """
        API response must always contain a numeric monthly_contribution field.
        The dashboard reads this field; if it is absent or non-numeric the
        'Net / month' KPI shows €0.00.
        """
        import app.routes.api as api_module

        uid = 'uid_dash_regression'
        accounts = [{'_id': 'acc1', 'balance': 2000.0, 'offBudget': True}]
        now = datetime.now(timezone.utc)
        transactions = [{
            '_id': 'tx1',
            'type': 'transfer',
            'amount': 350.0,
            'accountId': 'checking',
            'toAccountId': 'acc1',
            'date': datetime(now.year, now.month, 1, tzinfo=timezone.utc),
        }]
        mock_db = MagicMock()
        self._setup_firestore(api_module, mock_db)

        response = _call_projection_inner(
            api_module, uid, mock_db,
            accounts=accounts,
            transactions=transactions,
        )
        data = response.get_json()

        # The field must exist
        self.assertIn('monthly_contribution', data)
        # It must not be None
        self.assertIsNotNone(data['monthly_contribution'])
        # It must be numeric (not a string or object)
        self.assertIsInstance(data['monthly_contribution'], (int, float))
        # It must equal the net transfer amount for a single month
        self.assertEqual(data['monthly_contribution'], 350.0)

    def test_monthly_net_field_absent_from_response(self):
        """
        The field 'monthly_net' must NOT be present in the API response.
        Its presence would indicate a regression back to the old (wrong) naming
        that caused the dashboard 'Net / month' KPI to always show €0.00.
        """
        import app.routes.api as api_module

        uid = 'uid_no_monthly_net'
        mock_db = MagicMock()
        self._setup_firestore(api_module, mock_db)

        response = _call_projection_inner(
            api_module, uid, mock_db, accounts=[], transactions=[]
        )
        data = response.get_json()

        self.assertNotIn('monthly_net', data)

    def test_response_contains_all_dashboard_kpi_fields(self):
        """
        All fields consumed by the dashboard KPI cards must be present in the
        API response: monthly_contribution, balance_12m, balance_24m, balance_36m.
        """
        import app.routes.api as api_module

        uid = 'uid_kpi_fields'
        accounts = [{'_id': 'acc1', 'balance': 5000.0, 'offBudget': True}]
        mock_db = MagicMock()
        self._setup_firestore(api_module, mock_db)

        response = _call_projection_inner(
            api_module, uid, mock_db,
            accounts=accounts,
            transactions=[],
            user_settings={'monthlySavings': 200.0},
        )
        data = response.get_json()

        for field in ('monthly_contribution', 'balance_12m', 'balance_24m', 'balance_36m'):
            self.assertIn(field, data, f"Expected field '{field}' missing from projection response")


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
