from flask import Flask, render_template

def create_app(config_name='development'):
    from config.config import config
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Register blueprints
    from app.routes.main import main_bp
    from app.routes.whatsapp import whatsapp_bp  # ← ADD THIS
    app.register_blueprint(main_bp)
    app.register_blueprint(whatsapp_bp)           # ← ADD THIS

    @app.after_request
    def set_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        return response
    
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('index.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return render_template('index.html'), 500
    
    return app
