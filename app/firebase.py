# app/firebase.py
import os
import json
import logging
import firebase_admin
from firebase_admin import credentials, firestore

logger = logging.getLogger(__name__)

db = None  # Set to a Firestore client once Firebase is successfully initialized.


def init_firebase():
    """Initialize the Firebase Admin SDK.

    Returns True on success, False when credentials are not available
    (e.g. during local development without a service-account key).
    """
    if firebase_admin._apps:
        return True

    env_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")

    if env_json:
        try:
            cred_dict = json.loads(env_json)
            cred = credentials.Certificate(cred_dict)
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning("FIREBASE_SERVICE_ACCOUNT_JSON is invalid: %s", exc)
            return False
    elif os.path.exists("serviceAccountKey.json"):
        cred = credentials.Certificate("serviceAccountKey.json")
    else:
        logger.warning(
            "Firebase credentials not found. "
            "Set FIREBASE_SERVICE_ACCOUNT_JSON or provide serviceAccountKey.json. "
            "Firebase-dependent features will be disabled."
        )
        return False

    try:
        firebase_admin.initialize_app(cred)
        return True
    except Exception as exc:  # pragma: no cover
        logger.warning("Firebase initialization failed: %s", exc)
        return False


if init_firebase():
    db = firestore.client()
