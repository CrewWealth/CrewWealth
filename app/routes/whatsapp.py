from flask import Blueprint, request
from twilio.twiml.messaging_response import MessagingResponse
import firebase_admin
from firebase_admin import credentials, firestore
import os
import re

whatsapp_bp = Blueprint('whatsapp', __name__)

# Firebase init (only once)
if not firebase_admin._apps:
    cred = credentials.Certificate(os.getenv('FIREBASE_SERVICE_ACCOUNT_PATH'))
    firebase_admin.initialize_app(cred)

db = firestore.client()

@whatsapp_bp.route('/webhook/whatsapp', methods=['POST'])
def whatsapp_webhook():
    incoming_msg = request.form.get('Body', '').strip()
    from_number  = request.form.get('From', '').strip()
    resp = MessagingResponse()
    msg  = resp.message()
    msg.body(handle_message(incoming_msg, from_number))
    return str(resp)

def handle_message(text, phone):
    t = text.lower()
    if any(w in t for w in ['spent', 'paid', 'payment', 'expense']):
        return handle_expense(text, phone)
    elif any(w in t for w in ['received', 'salary', 'income', 'deposit']):
        return handle_income(text, phone)
    elif any(w in t for w in ['balance', 'how much', 'total', 'net worth']):
        return handle_balance(phone)
    elif any(w in t for w in ['add account', 'new account', 'create account']):
        return handle_new_account(text, phone)
    elif any(w in t for w in ['help', 'commands', 'menu']):
        return handle_help()
    else:
        return (
            "I didn't understand that 🤔\n\n"
            "Try:\n"
            "• *Spent €45 groceries*\n"
            "• *Received €2000 salary*\n"
            "• *Balance*\n"
            "• *Add account: Savings*\n"
            "• *Help*"
        )

def extract_amount(text):
    match = re.search(r'[€$]?\s*(\d+(?:[.,]\d{1,2})?)', text)
    return float(match.group(1).replace(',', '.')) if match else None

def get_user_by_phone(phone):
    clean_phone = phone.replace('whatsapp:', '')
    docs = db.collection('users').where('phone', '==', clean_phone).limit(1).get()
    for doc in docs:
        return doc.id, doc.to_dict()
    return None, None

def handle_expense(text, phone):
    amount = extract_amount(text)
    if not amount:
        return "I couldn't find an amount 💸\nTry: *Spent €45 groceries*"
    uid, _ = get_user_by_phone(phone)
    if not uid:
        return "Your phone isn't linked to a CrewWealth account.\nAdd it in Settings at crewwealth.onrender.com"
    db.collection('users').document(uid).collection('transactions').add({
        'type': 'expense',
        'amount': amount,
        'description': text,
        'source': 'whatsapp',
        'timestamp': firestore.SERVER_TIMESTAMP
    })
    return f"✅ Expense logged: €{amount:.2f}\n\nView it at crewwealth.onrender.com 📊"

def handle_income(text, phone):
    amount = extract_amount(text)
    if not amount:
        return "I couldn't find an amount 💰\nTry: *Received €2000 salary*"
    uid, _ = get_user_by_phone(phone)
    if not uid:
        return "Your phone isn't linked to a CrewWealth account.\nAdd it in Settings at crewwealth.onrender.com"
    db.collection('users').document(uid).collection('transactions').add({
        'type': 'income',
        'amount': amount,
        'description': text,
        'source': 'whatsapp',
        'timestamp': firestore.SERVER_TIMESTAMP
    })
    return f"✅ Income logged: €{amount:.2f}\n\nView it at crewwealth.onrender.com 📊"

def handle_balance(phone):
    uid, _ = get_user_by_phone(phone)
    if not uid:
        return "Your phone isn't linked to a CrewWealth account.\nAdd it in Settings at crewwealth.onrender.com"
    accounts = db.collection('users').document(uid).collection('accounts').get()
    total = sum(float(a.to_dict().get('balance', 0)) for a in accounts)
    return f"💰 Your current balance: *€{total:.2f}*\n\nFull overview: crewwealth.onrender.com"

def handle_new_account(text, phone):
    uid, _ = get_user_by_phone(phone)
    if not uid:
        return "Your phone isn't linked to a CrewWealth account.\nAdd it in Settings at crewwealth.onrender.com"
    match = re.search(r'(?:account[:\s]+)(.+)', text, re.IGNORECASE)
    account_name = match.group(1).strip() if match else "New Account"
    db.collection('users').document(uid).collection('accounts').add({
        'name': account_name,
        'balance': 0,
        'offBudget': False,
        'createdFrom': 'whatsapp',
        'timestamp': firestore.SERVER_TIMESTAMP
    })
    return f"✅ Account *{account_name}* created!\n\nSee it at crewwealth.onrender.com 🏦"

def handle_help():
    return (
        "🚢 *CrewWealth Bot Commands*\n\n"
        "💸 *Log expense:*\nSpent €45 groceries\n\n"
        "💰 *Log income:*\nReceived €2000 salary\n\n"
        "📊 *Check balance:*\nBalance\n\n"
        "🏦 *New account:*\nAdd account: Savings\n\n"
        "🌐 Full app: crewwealth.onrender.com"
    )