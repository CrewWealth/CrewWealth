# app/firebase.py
import firebase_admin
from firebase_admin import credentials, firestore
import os

def init_firebase():
    if not firebase_admin._apps:
        # On Render: uses environment variable
        # Locally: uses serviceAccountKey.json
        if os.environ.get('FIREBASE_CREDENTIALS'):
            import json
            cred_dict = json.loads(os.environ.get('FIREBASE_CREDENTIALS'))
            cred = credentials.Certificate(cred_dict)
        else:
            cred = credentials.Certificate('serviceAccountKey.json')
        
        firebase_admin.initialize_app(cred)

init_firebase()
db = firestore.client()
