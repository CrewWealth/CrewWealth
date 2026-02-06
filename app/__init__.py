from flask import Flask, render_template

def create_app(config_name='development'):
    """Application factory for CrewWealth"""
    from config.config import config
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Register blueprints - alleen main_bp nodig
    from app.routes.main import main_bp
    app.register_blueprint(main_bp)
    
    # Optioneel: Currency API behouden als je live wisselkoersen wilt
    # from app.routes.currency import currency_bp
    # app.register_blueprint(currency_bp)
    
    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('index.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return render_template('index.html'), 500
    
    return app