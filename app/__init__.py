import logging
from flask import Flask, jsonify, render_template, request

logger = logging.getLogger(__name__)


def create_app(config_name='development'):
    from config.config import config

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # ============================
    # Firebase initialiseren
    # ============================
    from app.firebase import init_firebase
    init_firebase()

    # ============================
    # Blueprints importeren
    # ============================
    from app.routes.main import main_bp
    from app.routes.income import income_bp
    from app.routes.currency import currency_bp
    from app.routes.api import api_bp
    # WhatsApp tijdelijk verwijderd:
    # from app.routes.whatsapp import whatsapp_bp

    # ============================
    # Blueprints registreren
    # ============================
    app.register_blueprint(main_bp)
    app.register_blueprint(income_bp)
    app.register_blueprint(currency_bp)
    app.register_blueprint(api_bp)
    # app.register_blueprint(whatsapp_bp)

    # ============================
    # Security headers
    # ============================
    @app.after_request
    def set_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        return response

    # ============================
    # Error handlers
    # API routes (/api/*) always get JSON; everything else gets HTML.
    # ============================
    @app.errorhandler(404)
    def not_found_error(error):
        from flask import has_request_context
        if has_request_context() and request.path.startswith('/api/'):
            return jsonify({'error': 'Not found', 'path': request.path}), 404
        return render_template('index.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        from flask import has_request_context
        if has_request_context():
            logger.exception("Internal server error on %s", request.path)
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Internal server error'}), 500
        return render_template('index.html'), 500

    return app
