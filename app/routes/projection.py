# app/routes/projection.py
"""3-year wealth projection API endpoint.

POST /api/projection
  - Requires a valid Firebase ID token (Authorization: Bearer <token>)
  - Accepts JSON body with monthly income, spending, and optional current savings
  - Returns 36-month cumulative balance projection
"""
from datetime import date

from flask import Blueprint, g, jsonify, request

from app.auth import firebase_token_required

projection_bp = Blueprint('projection', __name__, url_prefix='/api')


def _month_label(base: date, offset: int) -> str:
    """Return a human-readable month label for base + offset months."""
    total_months = base.month - 1 + offset
    year = base.year + total_months // 12
    month = total_months % 12 + 1
    return date(year, month, 1).strftime('%b %Y')


@projection_bp.route('/projection', methods=['POST'])
@firebase_token_required
def get_projection():
    """Calculate a 36-month (3-year) wealth projection.

    Request JSON body:
        monthly_income  (float) – average monthly income
        monthly_spending (float) – average monthly spending
        current_savings (float, optional) – starting balance, default 0

    Response JSON:
        {
          "success": true,
          "uid": "<firebase uid>",
          "monthly_net": <float>,
          "projection": [
            {"month": 1, "label": "May 2026", "balance": <float>},
            ...
          ]
        }
    """
    try:
        data = request.get_json(force=True) or {}
        monthly_income = float(data.get('monthly_income', 0))
        monthly_spending = float(data.get('monthly_spending', 0))
        current_savings = float(data.get('current_savings', 0))
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid input. monthly_income, monthly_spending '
                        'and current_savings must be numbers.'}), 400

    if monthly_income < 0:
        return jsonify({'error': 'monthly_income must be a non-negative number.'}), 400
    if monthly_spending < 0:
        return jsonify({'error': 'monthly_spending must be a non-negative number.'}), 400

    uid = g.uid
    monthly_net = monthly_income - monthly_spending
    balance = current_savings
    base_date = date.today().replace(day=1)

    projection = []
    for i in range(1, 37):
        balance += monthly_net
        projection.append({
            'month': i,
            'label': _month_label(base_date, i),
            'balance': round(balance, 2),
        })

    return jsonify({
        'success': True,
        'uid': uid,
        'monthly_net': round(monthly_net, 2),
        'projection': projection,
    })
