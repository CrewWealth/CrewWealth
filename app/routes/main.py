from flask import Blueprint, render_template, redirect, url_for

# Create Blueprint
main_bp = Blueprint('main', __name__)

# ============================================
# MAIN ROUTES (Protected by Firebase Auth in frontend)
# ============================================

@main_bp.route('/')
def index():
    """Home/Dashboard page"""
    return render_template('index.html')

@main_bp.route('/budget')
def budget():
    """Budget & Accounts management page"""
    return render_template('budget.html')

@main_bp.route('/goals')
def goals():
    """Financial Goals page"""
    return render_template('goals.html')

@main_bp.route('/reports')
def reports():
    """Reports and Analytics page"""
    return render_template('reports.html')

@main_bp.route('/settings')
def settings():
    """User Settings page"""
    return render_template('settings.html')

# ============================================
# AUTH ROUTES (Handled by Firebase Auth in frontend)
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
# REDIRECT ROUTES (For convenience)
# ============================================

@main_bp.route('/logout')
def logout():
    """Redirect to login - actual logout handled by Firebase in frontend"""
    return redirect(url_for('main.login'))

@main_bp.route('/dashboard')
def dashboard():
    """Redirect /dashboard to /"""
    return redirect(url_for('main.index'))

@main_bp.route('/accounts')
def accounts():
    """Redirect /accounts to /budget"""
    return redirect(url_for('main.budget'))