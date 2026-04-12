from flask import Blueprint, render_template, redirect, url_for, request
from twilio.twiml.messaging_response import MessagingResponse
import firebase_admin
from firebase_admin import firestore

# Create Blueprint
main_bp = Blueprint('main', __name__)


def _get_user_by_phone(phone):
    if not phone:
        return None
    users_ref = firestore.client().collection('users')
    query = users_ref.where('phone', '==', phone).limit(1).get()
    if not query:
        return None
    return query[0]


def _get_user_total_balance(user_doc):
    if not user_doc:
        return 0.0
    total = 0.0
    for account_doc in user_doc.reference.collection('accounts').get():
        data = account_doc.to_dict() or {}
        try:
            total += float(data.get('balance', 0) or 0)
        except (TypeError, ValueError):
            continue
    return total


def _get_user_currency(user_doc):
    if not user_doc:
        return 'EUR'
    data = user_doc.to_dict() or {}
    currency = (
        data.get('baseCurrency')
        or (data.get('settings') or {}).get('currency')
        or 'EUR'
    )
    return str(currency).upper()

@main_bp.route('/whatsapp', methods=['POST'])
def whatsapp_webhook():
    incoming = request.form.get('Body', '').strip().lower()
    phone = request.form.get('From', '')
    
    if incoming.startswith('link '):
        email = incoming[5:].strip()
        users_ref = firestore.client().collection('users')
        user_query = users_ref.where('email', '==', email).limit(1).get()
        
        if user_query:
            user_doc = user_query[0]
            user_data = user_doc.to_dict()
            user_doc.reference.update({
                'phone': phone,
                'linkedAt': firestore.SERVER_TIMESTAMP
            })
            resp = MessagingResponse()
            resp.message(f"✅ Linked! Welcome to CrewWealth, {user_data.get('name', 'Crew')}!\nSend *balance* to see your budget. 🚢")
            return str(resp)
        
        resp = MessagingResponse()
        resp.message("❌ No account found. Register at crewwealth.onrender.com first.")
        return str(resp)
    
    elif incoming == 'balance':
        user_doc = _get_user_by_phone(phone)
        resp = MessagingResponse()
        if not user_doc:
            resp.message("❌ No linked account found. Use *link email@crewwealth.app* first.")
            return str(resp)

        total_balance = _get_user_total_balance(user_doc)
        currency = _get_user_currency(user_doc)
        resp.message(f"💰 Balance: {total_balance:.2f} {currency}")
        return str(resp)
    
    resp = MessagingResponse()
    resp.message("""
🚢 CrewWealth Bot
• *balance* - See balance
• *link email@crewwealth.app* - Link account  
• *spent <amount> <note>* - Log expense
• *help* - Show this
    """)
    return str(resp)


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

@main_bp.route('/fx')
def fx_center():
    """Advanced FX settings page"""
    return render_template('fx.html')

@main_bp.route('/day3')
def day3_center():
    """Day 3 integrated collaboration and forecasting page"""
    return render_template('day3.html')

@main_bp.route('/migrate-goals')
def migrate_goals():
    """Goals Migration page"""
    return render_template('migrate-goals.html')

@main_bp.route('/login')
def login():
    """Login page"""
    return render_template('login.html')

@main_bp.route('/Login')
def login_case_redirect():
    """Redirect /Login to /login for case-insensitive robustness (302 so browsers don't cache permanently)"""
    return redirect(url_for('main.login', **request.args), code=302)

@main_bp.route('/register')
def register():
    """Registration page"""
    return render_template('register.html')

@main_bp.route('/logout')
def logout():
    """Redirect to login (Firebase handles actual logout)"""
    return redirect(url_for('main.login'))

@main_bp.route('/dashboard')
def dashboard():
    """Redirect /dashboard to /"""
    return redirect(url_for('main.index'))

@main_bp.route('/income')
def income_page():
    """Income calculator / overview page"""
    return render_template('income.html')
