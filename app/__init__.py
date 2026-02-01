from flask import Flask

def create_app(config_name='development'):
    """Application factory"""
    from config.config import config
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    db.init_app(app)
    
    # Register blueprints
    from app.routes.main import main_bp
    from app.routes.income import income_bp
    from app.routes.currency import currency_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(income_bp)
    app.register_blueprint(currency_bp)

    
    return app
