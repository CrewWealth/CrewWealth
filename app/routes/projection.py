"""Flask blueprint: /api/projection/<uid>

Returns a 36-month (3-year) wealth projection for the authenticated user.

Security
--------
Every request must carry a valid Firebase ID token in the
``Authorization: Bearer <token>`` header.  The token is verified with the
Firebase Admin SDK, and the decoded ``uid`` must match the ``<uid>`` URL
parameter so users can never read each other's projections.

Scenarios
---------
Three scenarios are always returned:

- **conservative** – monthly net multiplied by 0.80 (−20 %)
- **base**         – monthly net as-is
- **optimistic**   – monthly net multiplied by 1.15 (+15 %)

Input
-----
Pass the current month's numbers as query parameters so the frontend can
supply the values it already fetched from Firestore, avoiding a redundant
server-side Firestore round-trip:

    GET /api/projection/<uid>?monthly_income=3000&monthly_expenses=2000

When the query params are absent (both default to 0) the endpoint attempts
a server-side Firestore read for the current calendar month.
"""

from __future__ import annotations

import calendar
import logging
from datetime import datetime
from functools import wraps

from flask import Blueprint, current_app, jsonify, request

logger = logging.getLogger(__name__)

projection_bp = Blueprint("projection", __name__, url_prefix="/api")


# ---------------------------------------------------------------------------
# Helpers – lazy imports keep Firebase optional
# ---------------------------------------------------------------------------

def _firebase_auth():
    """Return the ``firebase_admin.auth`` module if Firebase is ready."""
    try:
        import firebase_admin
        from firebase_admin import auth as _auth

        if firebase_admin._apps:
            return _auth
    except Exception:
        pass
    return None


def _firestore_db():
    """Return the Firestore client if Firebase is ready."""
    try:
        from app.firebase import db  # noqa: PLC0415

        return db
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Auth decorator
# ---------------------------------------------------------------------------

def require_firebase_auth(f):
    """Verify the ``Authorization: Bearer <token>`` header.

    - In production the token is cryptographically verified.
    - In *debug* mode, when Firebase credentials are absent, verification is
      skipped so developers can test without a service-account key.
    - The decoded ``uid`` is compared to the ``uid`` URL parameter; a
      mismatch always results in a 403, even in debug mode.
    """

    @wraps(f)
    def decorated(*args, **kwargs):
        uid = kwargs.get("uid", "")

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header"}), 401

        token = auth_header[7:]
        firebase_auth = _firebase_auth()

        if firebase_auth is None:
            # Firebase Admin SDK not configured.
            if not current_app.debug:
                return jsonify({"error": "Firebase not configured on server"}), 503
            # Debug mode: skip cryptographic verification, but still parse the
            # token payload for the uid claim (without signature check).
            import base64
            import json as _json

            try:
                # JWT payload is the second base64url-encoded segment.
                payload_b64 = token.split(".")[1]
                # Add padding if needed.
                payload_b64 += "=" * (-len(payload_b64) % 4)
                payload = _json.loads(base64.urlsafe_b64decode(payload_b64))
                token_uid = payload.get("sub") or payload.get("uid", "")
            except Exception:
                token_uid = ""
        else:
            try:
                decoded = firebase_auth.verify_id_token(token)
                token_uid = decoded.get("uid", "")
            except Exception as exc:
                logger.warning("Token verification failed: %s", exc)
                return jsonify({"error": "Invalid or expired token"}), 401

        if uid and token_uid != uid:
            return jsonify({"error": "Forbidden: UID mismatch"}), 403

        return f(*args, **kwargs)

    return decorated


# ---------------------------------------------------------------------------
# Projection calculation
# ---------------------------------------------------------------------------

_SCENARIOS: dict[str, float] = {
    "conservative": 0.80,
    "base": 1.00,
    "optimistic": 1.15,
}


def _month_label(start: datetime, offset: int) -> str:
    """Return a 'Mon YYYY' label for *start* + *offset* months."""
    total_months = start.month - 1 + offset  # 0-based
    year = start.year + total_months // 12
    month = total_months % 12 + 1
    return datetime(year, month, 1).strftime("%b %Y")


def _build_projection(monthly_net: float, start: datetime) -> dict:
    """Build a 36-month projection for a single scenario."""
    months_data: list[dict] = []
    balance = 0.0

    for i in range(1, 37):
        balance += monthly_net
        months_data.append(
            {
                "month": i,
                "label": _month_label(start, i),
                "balance": round(balance, 2),
            }
        )

    return {
        "monthly_net": round(monthly_net, 2),
        "year1_balance": months_data[11]["balance"],
        "year2_balance": months_data[23]["balance"],
        "year3_balance": months_data[35]["balance"],
        "months": months_data,
    }


def _fetch_monthly_totals(uid: str) -> tuple[float, float]:
    """Try to read the current month's income/expense totals from Firestore."""
    db = _firestore_db()
    if db is None:
        return 0.0, 0.0

    try:
        now = datetime.now()
        month_start = datetime(now.year, now.month, 1)
        last_day = calendar.monthrange(now.year, now.month)[1]
        month_end = datetime(now.year, now.month, last_day, 23, 59, 59)

        docs = (
            db.collection("users")
            .document(uid)
            .collection("transactions")
            .where("date", ">=", month_start)
            .where("date", "<=", month_end)
            .stream()
        )

        income = 0.0
        expenses = 0.0
        for doc in docs:
            data = doc.to_dict()
            amount = abs(float(data.get("amount", 0)))
            tx_type = data.get("type", "")
            if tx_type in ("salary", "deposit"):
                income += amount
            elif tx_type == "payment":
                expenses += amount

        return income, expenses
    except Exception as exc:  # pragma: no cover
        logger.warning("Firestore read failed for uid %s: %s", uid, exc)
        return 0.0, 0.0


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------

@projection_bp.route("/projection/<uid>")
@require_firebase_auth
def get_projection(uid: str):
    """Return a 36-month wealth projection in three scenarios (JSON).

    Query parameters
    ----------------
    monthly_income : float, optional
        The user's monthly income.  When omitted the server reads the current
        month's transactions from Firestore.
    monthly_expenses : float, optional
        The user's monthly expenses.  Same fallback as above.

    Response shape
    --------------
    .. code-block:: json

        {
          "uid": "...",
          "monthly_income": 3000.0,
          "monthly_expenses": 2000.0,
          "scenarios": {
            "conservative": {
              "monthly_net": 800.0,
              "year1_balance": 9600.0,
              "year2_balance": 19200.0,
              "year3_balance": 28800.0,
              "months": [{"month": 1, "label": "May 2026", "balance": 800.0}, ...]
            },
            "base": { ... },
            "optimistic": { ... }
          }
        }
    """
    # --- Parse / validate query params -----------------------------------
    try:
        monthly_income = float(request.args.get("monthly_income", 0))
        monthly_expenses = float(request.args.get("monthly_expenses", 0))
    except (ValueError, TypeError):
        return jsonify({"error": "monthly_income and monthly_expenses must be numbers"}), 400

    if monthly_income < 0 or monthly_expenses < 0:
        return jsonify({"error": "monthly_income and monthly_expenses must be non-negative"}), 400

    # --- Fallback to Firestore when params are absent -------------------
    if monthly_income == 0 and monthly_expenses == 0:
        monthly_income, monthly_expenses = _fetch_monthly_totals(uid)

    monthly_net = monthly_income - monthly_expenses
    start = datetime.now()

    # --- Build all scenarios --------------------------------------------
    scenarios = {
        name: _build_projection(monthly_net * multiplier, start)
        for name, multiplier in _SCENARIOS.items()
    }

    return jsonify(
        {
            "uid": uid,
            "monthly_income": round(monthly_income, 2),
            "monthly_expenses": round(monthly_expenses, 2),
            "scenarios": scenarios,
        }
    )
