# app/firebase.py
import os
import json
import firebase_admin
from firebase_admin import credentials, firestore


def init_firebase():
    if firebase_admin._apps:
        return

    env_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")

    if env_json:
        cred_dict = json.loads(env_json)
        cred = credentials.Certificate(cred_dict)
    else:
        if not os.path.exists("serviceAccountKey.json"):
            raise FileNotFoundError(
                "serviceAccountKey.json not found and FIREBASE_SERVICE_ACCOUNT_JSON not set"
            )
        cred = credentials.Certificate("serviceAccountKey.json")

    firebase_admin.initialize_app(cred)


init_firebase()
db = firestore.client()
