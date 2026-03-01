# app/routes/whatsapp.py

from flask import Blueprint, request
from twilio.twiml.messaging_response import MessagingResponse
from app.firebase import db # type: ignore
from google.cloud import firestore as fs
import re

whatsapp_bp = Blueprint('whatsapp', __name__)

def send_reply(resp, message):
    resp.message(message)

def get_user_by_phone(phone):
    users = db.collection('users').where('phone', '==', phone).limit(1).get()
    return users[0] if users else None

def get_user_by_email(email):
    users = db.collection('users').where('email', '==', email).limit(1).get()
    return users[0] if users else None

@whatsapp_bp.route('/webhook/whatsapp', methods=['POST'])
def whatsapp_webhook():
    incoming = request.form.get('Body', '').strip().lower()
    sender   = request.form.get('From', '').replace('whatsapp:', '')
    resp     = MessagingResponse()

    # ── LINK command ──────────────────────────────────────────────
    if incoming.startswith('link '):
        email = incoming.split('link ')[1].strip()
        user  = get_user_by_email(email)

        if not user:
            send_reply(resp, "❌ No CrewWealth account found for that email.\nMake sure you sign up first at crewwealth.app")
            return str(resp)

        # Check if phone is already linked to a different account
        existing = get_user_by_phone(sender)
        if existing and existing.id != user.id:
            send_reply(resp, "⚠️ This WhatsApp number is already linked to a different account.")
            return str(resp)

        db.collection('users').document(user.id).update({
            'phone': sender
        })
        name = user.to_dict().get('name', 'there')
        send_reply(resp, f"✅ Linked! Welcome to CrewWealth, {name}!\n\nSend *help* to see what I can do for you. 🚢")
        return str(resp)

    # ── Require linked account for all other commands ─────────────
    user = get_user_by_phone(sender)
    if not user:
        send_reply(resp,
            "👋 Welcome to CrewWealth!\n\n"
            "To get started, link your account:\n"
            "*link your@email.com*\n\n"
            "Don't have an account yet? Sign up at crewwealth.app"
        )
        return str(resp)

    user_id   = user.id
    user_data = user.to_dict()

    # ── HELP ──────────────────────────────────────────────────────
    if incoming == 'help':
        send_reply(resp,
            "💰 *CrewWealth Bot*\n\n"
            "*Transactions:*\n"
            "• spent €20 groceries\n"
            "• earned €500 salary\n\n"
            "*Overview:*\n"
            "• balance\n"
            "• budgets\n\n"
            "*Account:*\n"
            "• unlink (remove WhatsApp)\n"
            "• help"
        )

    # ── UNLINK ────────────────────────────────────────────────────
    elif incoming == 'unlink':
        db.collection('users').document(user_id).update({
            'phone': fs.DELETE_FIELD
        })
        send_reply(resp, "✅ Your WhatsApp has been unlinked from CrewWealth.")

    # ── SPENT / EARNED ────────────────────────────────────────────
    elif incoming.startswith('spent ') or incoming.startswith('earned '):
        t_type  = 'expense' if incoming.startswith('spent ') else 'income'
        pattern = r'(spent|earned)\s+[€$]?([\d.]+)\s+(.*)'
        match   = re.match(pattern, incoming)

        if not match:
            send_reply(resp, "⚠️ Format: *spent €20 groceries* or *earned €500 salary*")
        else:
            amount      = float(match.group(2))
            description = match.group(3).capitalize()
            db.collection('users').document(user_id).collection('transactions').add({
                'type':        t_type,
                'amount':      amount,
                'description': description,
                'date':        fs.SERVER_TIMESTAMP,
                'source':      'whatsapp'
            })
            emoji = '💸' if t_type == 'expense' else '💰'
            send_reply(resp, f"{emoji} Logged: {description} — €{amount:.2f}")

    # ── BALANCE ───────────────────────────────────────────────────
    elif incoming == 'balance':
        txns    = db.collection('users').document(user_id).collection('transactions').get()
        income  = sum(t.to_dict()['amount'] for t in txns if t.to_dict().get('type') == 'income')
        expense = sum(t.to_dict()['amount'] for t in txns if t.to_dict().get('type') == 'expense')
        balance = income - expense
        send_reply(resp,
            f"📊 *Your Balance*\n\n"
            f"Income:   €{income:.2f}\n"
            f"Expenses: €{expense:.2f}\n"
            f"─────────────\n"
            f"Balance:  €{balance:.2f}"
        )

    else:
        send_reply(resp, "🤔 I didn't understand that. Send *help* to see all commands.")

    return str(resp)
