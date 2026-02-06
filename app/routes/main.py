from flask import Blueprint, render_template, redirect, url_for

# Create Blueprint
main_bp = Blueprint('main', __name__)

# ============================================
# MAIN ROUTES
# ============================================

@main_bp.route('/')
def index():
    """Home/Dashboard page"""
    return render_template('index.html')

@main_bp.route('/budget')
def budget():
    """Budget & Accounts page"""
    return render_template('budget.html')

@main_bp.route('/goals')
def goals():
    """Financial Goals page"""
    return render_template('goals.html')

@main_bp.route('/reports')
def reports():
    """Reports page"""
    return render_template('reports.html')

@main_bp.route('/settings')
def settings():
    """Settings page"""
    return render_template('settings.html')

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

# ============================================
# REDIRECTS
# ============================================

@main_bp.route('/logout')
def logout():
    """Redirect to login (Firebase handles actual logout)"""
    return redirect(url_for('main.login'))

@main_bp.route('/dashboard')
def dashboard():
    """Redirect /dashboard to /"""
    return redirect(url_for('main.index'))

@main_bp.route('/income')
def income_redirect():
    """Redirect old /income to dashboard"""
    return redirect(url_for('main.index'))