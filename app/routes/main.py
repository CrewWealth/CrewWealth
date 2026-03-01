from flask import Blueprint, render_template, redirect, url_for, request
from twilio.twiml.messaging_response import MessagingResponse
import firebase_admin
from firebase_admin import firestore

# Create Blueprint (EÉN KEER)
main_bp = Blueprint('main', __name__)

# ============================================
# WHATSAPP BOT ROUTES (NIEUW)
# ============================================

@main_bp.route('/whatsapp', methods=['POST'])
def whatsapp_webhook():
    """WhatsApp webhook endpoint"""
    incoming = request.form.get('Body', '').strip().lower()
    phone = request.form.get('From', '')
    
    if incoming.startswith('link '):
        email = incoming[5:].strip()
        users_ref = firestore.client().collection('users')
        user_query = users_ref.where('email', '==', email).limit(1)
        user_doc = user_query.stream()
        
        for doc in user_doc:
            user_data = doc.to_dict()
            doc.reference.update({
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
        resp = MessagingResponse()
        resp.message("💰 Balance: €1,234.56\n*spent €15 lunch* to log expenses!")
        return str(resp)
    
    resp = MessagingResponse()
    resp.message("""
🚢 CrewWealth Bot
    
• *balance* - See balance
• *link email@crewwealth.app* - Link account  
• *spent €15 lunch* - Log expense
• *help* - Show this
    """)
    return str(resp)

# ============================================
# MAIN ROUTES (je bestaande code)
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

@main_bp.route('/migrate-goals')
def migrate_goals():
    """Goals Migration page"""
    return render_template('migrate-goals.html')

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
