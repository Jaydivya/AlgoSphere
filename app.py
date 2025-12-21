# app.py - FIXED FOR RENDER + SQLALCHEMY
import os
from flask import Flask, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    
    # Config
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-key")
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///algo_users.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    # CRITICAL: Init SQLAlchemy FIRST
    db.init_app(app)
    
    # Login manager
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    
    @login_manager.user_loader
    def load_user(user_id):
        from models import User
        return User.query.get(int(user_id))
    
    # Create tables BEFORE blueprints
    with app.app_context():
        db.create_all()
    
    # Blueprints (AFTER db.init_app)
    from auth_routes import auth_bp
    from dashboard_routes import dash_bp
    from broker_routes import broker_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(dash_bp)
    app.register_blueprint(broker_bp)
    
    @app.route('/')
    def index():
        return redirect(url_for('auth.login'))
    
    @app.route('/health')
    def health():
        return {'status': 'healthy'}, 200
    
    return app

if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
