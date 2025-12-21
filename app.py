# app.py
from flask import Flask
from flask_login import LoginManager
from models import db, User

# Blueprints
from auth_routes import auth_bp
from dashboard_routes import dash_bp
from broker_routes import broker_bp


def create_app():
    app = Flask(__name__)

    # ----- Core config -----
    app.config["SECRET_KEY"] = "change-this-in-production"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///algo_users.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # ----- Init extensions -----
    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # ----- Register blueprints -----
    app.register_blueprint(auth_bp)
    app.register_blueprint(dash_bp)
    app.register_blueprint(broker_bp)

    # ----- Create DB tables -----
    with app.app_context():
        db.create_all()

    return app


# For simple running: `python app.py`
if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
