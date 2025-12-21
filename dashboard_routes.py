# dashboard_routes.py
from datetime import datetime, date, timedelta

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from models import db, BrokerConnection, StrategyConfig, Trade
from pya3 import Aliceblue  # stub/adjust if not using yet

dash_bp = Blueprint("dash", __name__)


def get_alice_connection():
    """Return (alice_client, is_broker_connected, is_paper) for current_user."""
    conn = BrokerConnection.query.filter_by(user_id=current_user.id).first()
    if not conn:
        return None, False, True

    # Use trade_mode + paper_trade for compatibility
    mode = conn.trade_mode or ("PAPER" if conn.paper_trade else "LIVE")
    is_paper = mode != "LIVE"

    if is_paper or not conn.api_key or not conn.session_id:
        return None, False, True

    try:
        alice = Aliceblue(
            user_id=current_user.email,  # or stored client_id
            api_key=conn.api_key,
            session_id=conn.session_id,
        )
        return alice, True, False
    except Exception as e:
        print("Alice connect error:", e)
        return None, False, True


@dash_bp.route("/dashboard")
@login_required
def dashboard():
    """Main AlgoSphere dashboard with stats, equity curve and bots."""
    # Defaults
    balance = [{"net": 0.0, "cashmarginavailable": 0.0}]
    nifty_ltp = 0.0
    banknifty_ltp = 0.0
    profile = type("P", (), {"accountName": current_user.email})()
    is_broker_connected = False
    is_paper = True

    alice, is_broker_connected, is_paper = get_alice_connection()

    if alice and is_broker_connected:
        # Balance
        try:
            bal = alice.get_balance()
            if bal:
                balance = bal
        except Exception as e:
            print("Balance error:", e)

        # Profile
        try:
            prof = alice.get_profile()
            if prof and hasattr(prof, "accountName"):
                profile = prof
        except Exception as e:
            print("Profile error:", e)

        # Indices
        try:
            n = alice.get_ltp("NSE", "NIFTY 50")
            if n:
                nifty_ltp = float(n.get("ltp", 0.0))

            b = alice.get_ltp("NSE", "NIFTY BANK")
            if b:
                banknifty_ltp = float(b.get("ltp", 0.0))
        except Exception as e:
            print("Index LTP error:", e)

    # Fallback demo values if no broker
    if not is_broker_connected:
        if balance[0]["net"] == 0.0:
            balance[0]["net"] = 100000.0
            balance[0]["cashmarginavailable"] = 100000.0
        if nifty_ltp == 0.0:
            nifty_ltp = 23000.0
        if banknifty_ltp == 0.0:
            banknifty_ltp = 49500.0

    # BankNIFTY ORB config
    cfg = StrategyConfig.query.filter_by(
        user_id=current_user.id, strategy_name="banknifty_orb_vwap"
    ).first()

    banknifty_orb_enabled = bool(cfg and cfg.enabled)
    banknifty_orb_lots = cfg.lots if cfg else 3
    banknifty_orb_target = cfg.target_points if cfg else 80
    banknifty_orb_stop = cfg.stop_points if cfg else 50

    # Equity curve: last 50 trades, cumulative PnL
    trades = (
        Trade.query.filter_by(user_id=current_user.id)
        .order_by(Trade.closed_at.asc())
        .limit(50)
        .all()
    )

    equity_labels = []
    equity_values = []
    cum = 0.0
    for t in trades:
        cum += t.pnl
        equity_labels.append(t.closed_at.strftime("%d-%b"))
        equity_values.append(round(cum, 2))

    return render_template(
        "dashboard.html",
        profile=profile,
        balance=balance,
        nifty_ltp=nifty_ltp,
        banknifty_ltp=banknifty_ltp,
        is_broker_connected=is_broker_connected,
        is_paper=is_paper,
        banknifty_orb_enabled=banknifty_orb_enabled,
        banknifty_orb_lots=banknifty_orb_lots,
        banknifty_orb_target=banknifty_orb_target,
        banknifty_orb_stop=banknifty_orb_stop,
        equity_labels=equity_labels,
        equity_values=equity_values,
    )


@dash_bp.route("/bots/banknifty_orb/deploy", methods=["POST"])
@login_required
def deploy_banknifty_orb():
    """Save/update BankNIFTY ORB config (lots) and enable it."""
    lots_raw = request.form.get("lots", "1")
    try:
        lots = int(lots_raw)
    except ValueError:
        flash("Invalid lot size. Use 1–10.", "danger")
        return redirect(url_for("dash.dashboard"))

    if lots < 1 or lots > 10:
        flash("Lots must be between 1 and 10.", "danger")
        return redirect(url_for("dash.dashboard"))

    cfg = StrategyConfig.query.filter_by(
        user_id=current_user.id, strategy_name="banknifty_orb_vwap"
    ).first()

    if not cfg:
        cfg = StrategyConfig(
            user_id=current_user.id,
            strategy_name="banknifty_orb_vwap",
            enabled=True,
            lots=lots,
            target_points=80,
            stop_points=50,
            daily_max_loss=3000,
        )
        db.session.add(cfg)
    else:
        cfg.enabled = True
        cfg.lots = lots

    db.session.commit()

    conn = BrokerConnection.query.filter_by(user_id=current_user.id).first()
    if conn and not conn.paper_trade and (conn.trade_mode == "LIVE"):
        flash(f"BankNIFTY ORB deployed with {lots} lots (LIVE).", "success")
    else:
        flash(f"BankNIFTY ORB deployed with {lots} lots (Paper/Demo).", "success")

    return redirect(url_for("dash.dashboard"))


@dash_bp.route("/reports")
@login_required
def reports():
    """Basic reports page with date filter and summary stats."""
    period = request.args.get("period", "daily")
    today = date.today()
    start_date = today
    end_date = today

    if period == "weekly":
        start_date = today - timedelta(days=7)
    elif period == "monthly":
        start_date = today.replace(day=1)

    from_str = request.args.get("from")
    to_str = request.args.get("to")
    if from_str and to_str:
        try:
            start_date = datetime.strptime(from_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(to_str, "%Y-%m-%d").date()
            period = "custom"
        except ValueError:
            flash("Invalid date format. Use YYYY-MM-DD.", "danger")

    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date + timedelta(days=1), datetime.min.time())

    trades = (
        Trade.query
        .filter(Trade.user_id == current_user.id)
        .filter(Trade.closed_at >= start_dt)
        .filter(Trade.closed_at < end_dt)
        .order_by(Trade.closed_at.desc())
        .all()
    )

    total_pnl = sum(t.pnl for t in trades)
    win_count = len([t for t in trades if t.pnl > 0])
    win_rate = (win_count / len(trades) * 100) if trades else 0.0

    return render_template(
        "reports.html",
        trades=trades,
        total_pnl=total_pnl,
        win_rate=win_rate,
        period=period,
        start_date=start_date,
        end_date=end_date,
    )
