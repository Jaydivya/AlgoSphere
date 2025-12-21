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
    broker_access_token = db.Column(db.String(255), nullable=True)


class Strategy(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    symbol = db.Column(db.String(20), default="BANKNIFTY")
    enabled = db.Column(db.Boolean, default=False)
    lots = db.Column(db.Integer, default=1)
    target = db.Column(db.Float, default=100.0)
    stop_loss = db.Column(db.Float, default=50.0)
    vwap_filter = db.Column(db.String(20), default="Above")  # NEW for ORB
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", backref="strategies")


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


with app.app_context():
    db.create_all()

    # seed admin user
    if not User.query.filter_by(email="admin@test.com").first():
        user = User(email="admin@test.com", password="admin123", broker_connected=False)
        db.session.add(user)
        db.session.commit()

    # seed default strategies for admin
    if not Strategy.query.first():
        admin = User.query.filter_by(email="admin@test.com").first()
        if admin:
            strategies = [
                Strategy(
                    name="BankNifty ORB",
                    description="5min Opening Range Breakout + VWAP filter",
                    symbol="BANKNIFTY",
                    lots=1,
                    target=3000,
                    stop_loss=3000,
                    vwap_filter="Above",
                    user_id=admin.id,
                ),
                Strategy(
                    name="Nifty ORB",
                    description="5min Opening Range Breakout",
                    symbol="NIFTY",
                    lots=1,
                    target=2000,
                    stop_loss=2000,
                    user_id=admin.id,
                ),
                Strategy(
                    name="MA Crossover",
                    description="20/50 EMA crossover",
                    symbol="BANKNIFTY",
                    lots=1,
                    target=1500,
                    stop_loss=1000,
                    user_id=admin.id,
                ),
            ]
            db.session.bulk_save_objects(strategies)
            db.session.commit()


# ---------- AliceBlue OAuth-like config ----------
ALICE_APP_ID = os.environ.get("ALICE_APP_ID", "YOUR_APP_ID")
ALICE_CLIENT_SECRET = os.environ.get("ALICE_CLIENT_SECRET", "YOUR_CLIENT_SECRET")
ALICE_REDIRECT_URI = os.environ.get(
    "ALICE_REDIRECT_URI", "http://127.0.0.1:5000/broker/callback"
)
ALICE_AUTH_URL = os.environ.get(
    "ALICE_AUTH_URL",
    "https://ant.aliceblueonline.com/oauth2/auth",
)
ALICE_TOKEN_URL = os.environ.get(
    "ALICE_TOKEN_URL",
    "https://ant.aliceblueonline.com/oauth2/token",
)


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
    # demo values – for UI testing only
    balance = [{
        "net": 152340.75,
        "cashmarginavailable": 98250.25,
    }]

    nifty_ltp = 24350.65
    banknifty_ltp = 52980.30

    # dummy P&L stats for the bottom cards (used only in template text)
    today_pnl = 2350.0
    win_rate = 62.5
    total_trades = 18

    return render_template(
        "dashboard.html",
        balance=balance,
        nifty_ltp=nifty_ltp,
        banknifty_ltp=banknifty_ltp,
        is_broker_connected=current_user.broker_connected,
        today_pnl=today_pnl,
        win_rate=win_rate,
        total_trades=total_trades,
    )



@app.route("/strategies")
@login_required
def strategies():
    user_strategies = Strategy.query.filter_by(user_id=current_user.id).all()
    return render_template("strategies.html", strategies=user_strategies)


@app.route("/deploy_strategy/<int:strategy_id>", methods=["POST"])
@login_required
def deploy_strategy(strategy_id):
    strategy = Strategy.query.get_or_404(strategy_id)
    if strategy.user_id != current_user.id:
        flash("Unauthorized", "error")
        return redirect(url_for("strategies"))

    strategy.enabled = not strategy.enabled
    status = "DEPLOYED" if strategy.enabled else "PAUSED"
    db.session.commit()

    flash(f"{strategy.name} {status}", "success")
    return redirect(url_for("strategies"))


@app.route("/services")
def services():
    return render_template("service.html")


@app.route("/team")
def team():
    return render_template("team.html")


@app.route("/connect_broker")
@login_required
def connect_broker():
    params = {
        "client_id": ALICE_APP_ID,
        "redirect_uri": ALICE_REDIRECT_URI,
        "response_type": "code",
        "state": str(current_user.id),
    }
    url = f"{ALICE_AUTH_URL}?{urlencode(params)}"
    return redirect(url)


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
