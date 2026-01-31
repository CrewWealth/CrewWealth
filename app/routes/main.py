from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
import os
from dotenv import load_dotenv

load_dotenv()

# Create Blueprint
main_bp = Blueprint('main', __name__)

# ============================================
# MAIN ROUTES
# ============================================

@main_bp.route('/')
def index():
    """Home/Dashboard page"""
    return render_template('index.html')

@main_bp.route('/goals')
def goals():
    """Financial Goals page"""
    return render_template('goals.html')

@main_bp.route('/income')
def income():
    """Income tracking page"""
    return render_template('income.html')

@main_bp.route('/family')
def family():
    """Family transfers tracking page"""
    return render_template('family.html')

@main_bp.route('/investments')
def investments():
    """Investment portfolio overview page"""
    return render_template('investments.html')

@main_bp.route('/budget')
def budget():
    """Budget management page - YNAB style"""
    return render_template('budget.html')


# ============================================
# AUTH ROUTES
# ============================================

@main_bp.route('/login')
def login():
    """Login page"""
    return render_template('login.html')

@main_bp.route('/register')
def register():
    """Registration page"""
    return render_template('register.html')

@main_bp.route('/onboarding')
def onboarding():
    """Onboarding wizard - post-registration"""
    return render_template('onboarding.html')

@main_bp.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    return redirect(url_for('main.login'))

# ============================================
# API ENDPOINTS
# ============================================

@main_bp.route('/api/goals', methods=['GET', 'POST'])
def api_goals():
    """API endpoint for goals CRUD"""
    if request.method == 'POST':
        pass
    return jsonify({'goals': []})

# ============================================
# ERROR HANDLERS
# ============================================

@main_bp.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@main_bp.errorhandler(500)
def server_error(error):
    return render_template('500.html'), 500
