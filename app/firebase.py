# app/firebase.py
import logging
import os
import json
import firebase_admin
from firebase_admin import credentials

logger = logging.getLogger(__name__)


def init_firebase():
    """Initialize Firebase Admin SDK.

    Credentials are resolved in order:
    1. ``FIREBASE_SERVICE_ACCOUNT_JSON`` environment variable (JSON string).
    2. ``serviceAccountKey.json`` file in the working directory.

    Returns ``True`` on success, ``False`` when credentials are unavailable so
    that the app can start without them (endpoints that require Firebase will
    return a 503 instead of crashing the whole process).
    """
    if firebase_admin._apps:
        return True

    env_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")

    if env_json:
        try:
            cred_dict = json.loads(env_json)
            cred = credentials.Certificate(cred_dict)
        except (ValueError, KeyError) as exc:
            logger.error("FIREBASE_SERVICE_ACCOUNT_JSON is set but could not be parsed: %s", exc)
            return False
    else:
        if not os.path.exists("serviceAccountKey.json"):
            logger.warning(
                "Firebase credentials not configured: set the "
                "FIREBASE_SERVICE_ACCOUNT_JSON environment variable or provide "
                "a serviceAccountKey.json file. Firebase-dependent endpoints "
                "will return 503 until credentials are available."
            )
            return False
        cred = credentials.Certificate("serviceAccountKey.json")

    try:
        firebase_admin.initialize_app(cred)
        logger.info("Firebase Admin SDK initialized successfully.")
        return True
    except Exception as exc:
        logger.error("firebase_admin.initialize_app failed: %s", exc)
        return False
