# broker_routes.py

from flask import Blueprint, request, redirect, url_for, flash
from flask_login import login_required, current_user

from models import db, BrokerConnection
from pya3 import Aliceblue
import traceback

# All broker URLs under /broker/...
broker_bp = Blueprint("broker", __name__, url_prefix="/broker")


@broker_bp.route("/paper", methods=["POST"])
@login_required
def enable_paper_legacy():
    """Enable paper trading mode (no real orders)."""
    conn = BrokerConnection.query.filter_by(user_id=current_user.id).first()
    if not conn:
        conn = BrokerConnection(user_id=current_user.id, broker="aliceblue")
        db.session.add(conn)

    conn.paper_trade = True
    conn.trade_mode = "PAPER"
    conn.api_key = None       # clear credentials for safety
    conn.session_id = None
    db.session.commit()

    flash("📝 Paper trading enabled. No real orders will be placed.", "success")
    return redirect(url_for("dash.dashboard"))


@broker_bp.route("/connect", methods=["POST"])
@login_required
def connect():
    """Connect to Alice Blue for LIVE trading (from dashboard form)."""
    client_id = request.form.get("client_id", "").strip()
    api_key = request.form.get("api_key", "").strip()
    password = request.form.get("password", "").strip()

    # Ensure all fields filled
    if not all([client_id, api_key, password]):
        flash("❌ All fields (Client ID, API Key, Password) are required.", "danger")
        return redirect(url_for("dash.dashboard"))

    # Explicit LIVE confirmation checkbox
    if not request.form.get("liveConfirm"):
        flash("❌ You must confirm LIVE TRADING before proceeding.", "danger")
        return redirect(url_for("dash.dashboard"))

    conn = BrokerConnection.query.filter_by(user_id=current_user.id).first()
    if not conn:
        conn = BrokerConnection(user_id=current_user.id, broker="aliceblue")
        db.session.add(conn)

    try:
        # Test real connection to Alice Blue
        print(f"Connecting with client_id={client_id[:4]}...")
        alice = Aliceblue(user_id=client_id, api_key=api_key)
        session_id = alice.get_session_id()

        # Success - store for live trading
        conn.api_key = api_key
        conn.session_id = session_id
        conn.paper_trade = False  # legacy flag
        conn.trade_mode = "LIVE"
        db.session.commit()

        flash("✅ LIVE TRADING ENABLED! Real orders will now execute.", "success")
        flash("⚠️ Monitor closely. Daily loss limit: ₹3000 per strategy.", "warning")
    except Exception as e:
        print(f"Broker connect error: {e}")
        print(traceback.format_exc())
        flash(f"❌ Connection failed: {str(e)}", "danger")
        flash("Check Client ID, API Key, and Trading Password.", "secondary")

    return redirect(url_for("dash.dashboard"))


@broker_bp.route("/status")
@login_required
def status():
    """API endpoint: broker connection status (for AJAX checks)."""
    conn = BrokerConnection.query.filter_by(user_id=current_user.id).first()
    if not conn:
        return {"connected": False, "live": False, "paper": True}

    # Determine effective mode
    mode = conn.trade_mode or ("PAPER" if conn.paper_trade else "LIVE")
    if mode != "LIVE":
        return {"connected": False, "live": False, "paper": True}

    if conn.api_key and conn.session_id:
        try:
            Aliceblue(
                user_id=current_user.email,
                api_key=conn.api_key,
                session_id=conn.session_id,
            )
            return {"connected": True, "live": True, "paper": False}
        except Exception:
            return {"connected": False, "live": False, "paper": True}

    return {"connected": False, "live": False, "paper": True}


@broker_bp.route("/mode/live", methods=["POST"])
@login_required
def enable_live():
    """Switch to LIVE mode; requires an existing valid session."""
    conn = BrokerConnection.query.filter_by(user_id=current_user.id).first()
    if not conn or not conn.session_id:
        flash("Connect broker first before enabling live.", "danger")
        return redirect(url_for("dash.dashboard"))

    conn.trade_mode = "LIVE"
    conn.paper_trade = False
    db.session.commit()

    flash("Switched to LIVE trading. Real orders will be sent.", "success")
    return redirect(url_for("dash.dashboard"))


@broker_bp.route("/mode/paper", methods=["POST"])
@login_required
def enable_paper_mode():
    """Switch to PAPER mode but keep connection row."""
    conn = BrokerConnection.query.filter_by(user_id=current_user.id).first()
    if not conn:
        # create a dummy connection row so mode is stored
        conn = BrokerConnection(user_id=current_user.id, trade_mode="PAPER")
        db.session.add(conn)
    else:
        conn.trade_mode = "PAPER"
        conn.paper_trade = True

    db.session.commit()
    flash("Switched to PAPER trading. Orders are simulated only.", "info")
    return redirect(url_for("dash.dashboard"))
