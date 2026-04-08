from flask import Flask, render_template


def create_app(config_name='development'):
    from config.config import config

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # ============================
    # Blueprints importeren
    # ============================
    from app.routes.main import main_bp
    from app.routes.income import income_bp
    from app.routes.currency import currency_bp
    from app.routes.projection import projection_bp
    # WhatsApp tijdelijk verwijderd:
    # from app.routes.whatsapp import whatsapp_bp

    # ============================
    # Blueprints registreren
    # ============================
    app.register_blueprint(main_bp)
    app.register_blueprint(income_bp)
    app.register_blueprint(currency_bp)
    app.register_blueprint(projection_bp)
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
    # Error handlers (HTML)
    # ============================
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('index.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        return render_template('index.html'), 500

    return app
