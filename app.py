import os
from datetime import datetime, date

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from dhanhq import dhanhq  # pip install dhanhq

app = Flask(__name__)
app.config["SECRET_KEY"] = "your-secret-key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# ---------- MODELS ----------

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    broker_connected = db.Column(db.Boolean, default=False)


class PaperTrade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(50))
    side = db.Column(db.String(10))
    qty = db.Column(db.Integer)
    entry_price = db.Column(db.Float)
    exit_price = db.Column(db.Float, nullable=True)
    pnl_rupees = db.Column(db.Float, default=0.0)
    trade_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default="OPEN")


class LiveTrade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(50))
    side = db.Column(db.String(10))
    qty = db.Column(db.Integer)
    entry_price = db.Column(db.Float)
    exit_price = db.Column(db.Float, nullable=True)
    pnl_rupees = db.Column(db.Float, default=0.0)
    trade_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default="OPEN")


# ---------- BROKER / GLOBALS ----------

DHAN_CLIENT_ID = os.environ.get("DHAN_CLIENT_ID")
DHAN_ACCESS_TOKEN = os.environ.get("DHAN_ACCESS_TOKEN")

broker_connection = None
trade_mode = "PAPER"  # "PAPER" or "LIVE"


def connect_broker() -> bool:
    """Create global Dhan connection."""
    global broker_connection
    try:
        broker_connection = dhanhq(client_id=DHAN_CLIENT_ID, access_token=DHAN_ACCESS_TOKEN)
        print("Broker connected:", broker_connection)
        return True
    except Exception as e:
        print("Broker connect error:", e)
        broker_connection = None
        return False


def get_fund_balance():
    """Return dict with available & total funds."""
    if not broker_connection:
        print("[funds] No broker_connection, using mock funds 1L")
        return {"available": 100000.0, "total": 100000.0}

    try:
        funds = broker_connection.get_fund_limits()
        # Keys per Dhan docs: availableBalance, sodLimit etc.
        available = float(funds.get("availableBalance", 0.0))
        total = float(funds.get("sodLimit", 0.0))
        return {"available": available, "total": total}
    except Exception as e:
        print("Funds error:", e)
        return {"available": 0.0, "total": 0.0}


def get_today_pnl(mode: str) -> float:
    """Sum today's closed trades PnL."""
    today = date.today()
    if mode == "PAPER":
        trades = PaperTrade.query.filter(
            db.func.date(PaperTrade.trade_date) == today,
            PaperTrade.exit_price.isnot(None),
        ).all()
    else:
        trades = LiveTrade.query.filter(
            db.func.date(LiveTrade.trade_date) == today,
            LiveTrade.exit_price.isnot(None),
        ).all()
    return sum(t.pnl_rupees for t in trades)


def get_index_ltp():
    """Temporary mock index prices (replace with real API later)."""
    nifty_ltp = 26000.0
    banknifty_ltp = 56000.0
    return nifty_ltp, banknifty_ltp


# ---------- ROUTES ----------

@app.route("/")
def home():
    return redirect(url_for("dashboard"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            return redirect(url_for("dashboard"))

        flash("Invalid credentials", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/toggle_broker", methods=["POST"])
def toggle_broker():
    """Connect or disconnect broker with one button."""
    global trade_mode, broker_connection

    if "user_id" not in session:
        return redirect(url_for("login"))

    user = db.session.get(User, session["user_id"])

    if user.broker_connected:
        # Disconnect
        broker_connection = None
        user.broker_connected = False
        trade_mode = "PAPER"
        flash("Broker disconnected. Switched to PAPER mode.", "success")
    else:
        ok = connect_broker()
        if ok:
            user.broker_connected = True
            trade_mode = "LIVE"
            flash("Broker connected. Live mode enabled.", "success")
        else:
            user.broker_connected = False
            flash("Broker connection failed. Check credentials.", "error")

    db.session.commit()
    return redirect(url_for("dashboard"))


@app.route("/toggle_mode", methods=["POST"])
def toggle_mode():
    """Switch between PAPER and LIVE (manual override)."""
    global trade_mode
    if "user_id" not in session:
        return redirect(url_for("login"))

    mode = request.form.get("mode", "paper").upper()
    trade_mode = "LIVE" if mode == "LIVE" else "PAPER"
    flash(f"Switched to {trade_mode} mode.", "success")
    return redirect(url_for("dashboard"))


@app.route("/deploy_paper_orb")
def deploy_paper_orb():
    """Demo: create one closed paper trade with PnL 2850."""
    if "user_id" not in session:
        return redirect(url_for("login"))

    trade = PaperTrade(
        symbol="BANKNIFTY CE",
        side="CE",
        qty=15,
        entry_price=150.0,
        exit_price=190.0,
        pnl_rupees=2850.0,
        status="CLOSED",
    )
    db.session.add(trade)
    db.session.commit()
    flash("Paper ORB deployed, +₹2850 P&L", "success")
    return redirect(url_for("dashboard"))


@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user = db.session.get(User, session["user_id"])

    funds = get_fund_balance()
    nifty_ltp, banknifty_ltp = get_index_ltp()

    today_pnl_paper = get_today_pnl("PAPER")
    today_pnl_live = get_today_pnl("LIVE")

    paper_trades = PaperTrade.query.order_by(PaperTrade.id.desc()).limit(20).all()
    live_trades = LiveTrade.query.order_by(LiveTrade.id.desc()).limit(20).all()

    return render_template(
        "dashboard.html",
        funds=funds,
        nifty_ltp=nifty_ltp,
        banknifty_ltp=banknifty_ltp,
        today_pnl_paper=today_pnl_paper,
        today_pnl_live=today_pnl_live,
        paper_trades=paper_trades,
        livetrades=live_trades,
        trade_mode=trade_mode,
        broker_connected=user.broker_connected,
    )


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        # Seed default admin user if not present
        if not User.query.filter_by(email="admin@test.com").first():
            user = User(
                email="admin@test.com",
                password=generate_password_hash("admin123"),
            )
            db.session.add(user)
            db.session.commit()

    app.run(debug=True)
