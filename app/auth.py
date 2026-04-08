# app/auth.py
"""Firebase ID token verification for Flask API endpoints.

Usage:
    from app.auth import firebase_token_required

    @some_bp.route('/api/protected', methods=['POST'])
    @firebase_token_required
    def protected_endpoint():
        uid = g.uid  # authenticated Firebase user ID
        ...
"""
from functools import wraps

from flask import g, jsonify, request
import firebase_admin.auth


def firebase_token_required(f):
    """Decorator that verifies a Firebase ID token from the Authorization header.

    Expects the request to contain an ``Authorization: Bearer <id_token>``
    header.  On success, ``flask.g.uid`` is set to the verified Firebase UID
    so the decorated view can use it directly.

    Returns HTTP 401 when the header is absent, malformed, or the token is
    invalid/expired.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid Authorization header. '
                            'Include "Authorization: Bearer <id_token>"'}), 401

        id_token = auth_header[len('Bearer '):]
        try:
            decoded_token = firebase_admin.auth.verify_id_token(id_token)
            g.uid = decoded_token['uid']
        except firebase_admin.auth.ExpiredIdTokenError:
            return jsonify({'error': 'Firebase ID token has expired. '
                            'Please sign in again.'}), 401
        except firebase_admin.auth.InvalidIdTokenError:
            return jsonify({'error': 'Firebase ID token is invalid.'}), 401
        except Exception:
            return jsonify({'error': 'Token verification failed.'}), 401

        return f(*args, **kwargs)
    return decorated_function
