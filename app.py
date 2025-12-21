# app.py - SINGLE FILE, NO BLUEPRINTS, RENDER-PROOF

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
)
import os

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "algo-secret")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150))


@login_manager.user_loader
def load_user(user_id):
    # Legacy warning is ok for now; can be upgraded later
    return User.query.get(int(user_id))


with app.app_context():
    db.create_all()
    # Create test user if missing
    if not User.query.filter_by(email="admin@test.com").first():
        user = User(email="admin@test.com", password="admin123")
        db.session.add(user)
        db.session.commit()


@app.route("/")
def index():
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        user = User.query.filter_by(email=email).first()
        if user and user.password == password:  # Simple password check
            login_user(user)
            return redirect(url_for("dashboard"))

        flash("Invalid credentials")

    return render_template("login.html")


@app.route("/dashboard")
@login_required
def dashboard():
    # Dummy values so dashboard.html works without full backend
    balance = [{"net": 0.0, "cashmarginavailable": 0.0}]
    nifty_ltp = 0.0
    banknifty_ltp = 0.0
    is_broker_connected = False
    banknifty_orb_enabled = False
    banknifty_orb_lots = 1
    banknifty_orb_target = 50
    banknifty_orb_stop = 30

    return render_template(
        "dashboard.html",
        balance=balance,
        nifty_ltp=nifty_ltp,
        banknifty_ltp=banknifty_ltp,
        is_broker_connected=is_broker_connected,
        banknifty_orb_enabled=banknifty_orb_enabled,
        banknifty_orb_lots=banknifty_orb_lots,
        banknifty_orb_target=banknifty_orb_target,
        banknifty_orb_stop=banknifty_orb_stop,
    )


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/health")
def health():
    return {"status": "healthy", "service": "AlgoSphere"}, 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
    