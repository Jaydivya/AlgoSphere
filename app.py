import os
import requests
from urllib.parse import urlencode

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user,
)

# ---------- Flask & DB setup ----------

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
    broker_connected = db.Column(db.Boolean, default=False)
    broker_access_token = db.Column(db.String(255), nullable=True)  # optional


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


with app.app_context():
    db.create_all()
    if not User.query.filter_by(email="admin@test.com").first():
        user = User(email="admin@test.com", password="admin123", broker_connected=False)
        db.session.add(user)
        db.session.commit()

# ---------- AliceBlue OAuth-like config (FILL THESE FROM DOCS) ----------

ALICE_APP_ID = os.environ.get("ALICE_APP_ID", "YOUR_APP_ID")
ALICE_CLIENT_SECRET = os.environ.get("ALICE_CLIENT_SECRET", "YOUR_CLIENT_SECRET")

# The redirect URL must also be registered in AliceBlue app settings
ALICE_REDIRECT_URI = os.environ.get(
    "ALICE_REDIRECT_URI", "http://127.0.0.1:5000/broker/callback"
)

# Replace these with REAL endpoints from AliceBlue API documentation
ALICE_AUTH_URL = os.environ.get(
    "ALICE_AUTH_URL",
    "https://ant.aliceblueonline.com/oauth2/auth",  # confirm in docs
)
ALICE_TOKEN_URL = os.environ.get(
    "ALICE_TOKEN_URL",
    "https://ant.aliceblueonline.com/oauth2/token",  # confirm in docs
)

# ---------------------------------------------------------------------


@app.route("/")
def index():
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        user = User.query.filter_by(email=email).first()
        if user and user.password == password:
            login_user(user)
            return redirect(url_for("dashboard"))
        flash("Invalid credentials")
    return render_template("login.html")


@app.route("/dashboard")
@login_required
def dashboard():
    # demo values – replace with real API calls later
    balance = [{"net": 0.0, "cashmarginavailable": 0.0}]
    nifty_ltp = 0.0
    banknifty_ltp = 0.0
    banknifty_orb_enabled = False
    banknifty_orb_lots = 1
    banknifty_orb_target = 50
    banknifty_orb_stop = 30

    return render_template(
        "dashboard.html",
        balance=balance,
        nifty_ltp=nifty_ltp,
        banknifty_ltp=banknifty_ltp,
        banknifty_orb_enabled=banknifty_orb_enabled,
        banknifty_orb_lots=banknifty_orb_lots,
        banknifty_orb_target=banknifty_orb_target,
        banknifty_orb_stop=banknifty_orb_stop,
        is_broker_connected=current_user.broker_connected,
    )


# -------------- Stocker pages (optional) -----------------


@app.route("/services")
def services():
    return render_template("service.html")


@app.route("/team")
def team():
    return render_template("team.html")


# -------------- Redirect to AliceBlue login --------------


@app.route("/connect_broker")
@login_required
def connect_broker():
    params = {
        "client_id": ALICE_APP_ID,
        "redirect_uri": ALICE_REDIRECT_URI,
        "response_type": "code",  # or as per their docs
        "state": str(current_user.id),
        # add "scope" etc if required by AliceBlue
    }
    url = f"{ALICE_AUTH_URL}?{urlencode(params)}"
    return redirect(url)


# -------------- Callback after AliceBlue login -----------


@app.route("/broker/callback")
def broker_callback():
    code = request.args.get("code")
    state = request.args.get("state")

    if not code:
        flash("Broker connect failed: missing code.")
        return redirect(url_for("dashboard"))

    if not current_user.is_authenticated:
        flash("Login again before connecting broker.")
        return redirect(url_for("login"))

    try:
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": ALICE_REDIRECT_URI,
            "client_id": ALICE_APP_ID,
            "client_secret": ALICE_CLIENT_SECRET,
        }
        resp = requests.post(ALICE_TOKEN_URL, data=data, timeout=15)
        resp.raise_for_status()
        token_data = resp.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise Exception("No access_token in response")

        current_user.broker_connected = True
        current_user.broker_access_token = access_token
        db.session.commit()
        flash("Broker connected via AliceBlue.")
    except Exception as e:
        current_user.broker_connected = False
        current_user.broker_access_token = None
        db.session.commit()
        flash(f"Broker connect failed: {e}")

    return redirect(url_for("dashboard"))


@app.route("/disconnect_broker", methods=["POST"])
@login_required
def disconnect_broker():
    current_user.broker_connected = False
    current_user.broker_access_token = None
    db.session.commit()
    flash("Broker disconnected.")
    return redirect(url_for("dashboard"))


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
