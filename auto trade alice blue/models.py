# models.py
from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
import bcrypt

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.LargeBinary(60), nullable=False)

    trades = db.relationship("Trade", backref="user", lazy=True)
    broker_connections = db.relationship("BrokerConnection", backref="user", lazy=True)
    strategies = db.relationship("StrategyConfig", backref="user", lazy=True)

    def set_password(self, password: str):
        self.password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

    def check_password(self, password: str) -> bool:
        return bcrypt.checkpw(password.encode(), self.password_hash)


class BrokerConnection(db.Model):
    __tablename__ = "broker_connection"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    # Broker identity
    broker = db.Column(db.String(32), default="aliceblue")

    # Credentials / session
    api_key = db.Column(db.String(128))
    session_id = db.Column(db.String(256))

    # Old flag – keep for compatibility with existing routes
    paper_trade = db.Column(db.Boolean, default=True)

    # New mode field: "LIVE" / "PAPER"
    trade_mode = db.Column(db.String(10), default="PAPER")


class StrategyConfig(db.Model):
    """User strategy settings (lots, targets, etc.)."""

    __tablename__ = "strategy_config"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    strategy_name = db.Column(db.String(100), nullable=False)  # "banknifty_orb_vwap"
    enabled = db.Column(db.Boolean, default=False)

    lots = db.Column(db.Integer, default=1)
    target_points = db.Column(db.Integer, default=80)
    stop_points = db.Column(db.Integer, default=50)
    daily_max_loss = db.Column(db.Integer, default=3000)


class Trade(db.Model):
    __tablename__ = "trade"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    strategy_name = db.Column(db.String(100), nullable=False)
    symbol = db.Column(db.String(100), nullable=False)
    side = db.Column(db.String(4), nullable=False)  # BUY/SELL
    qty = db.Column(db.Integer, nullable=False)

    entry_price = db.Column(db.Float, nullable=False)
    exit_price = db.Column(db.Float, nullable=False)
    pnl = db.Column(db.Float, nullable=False)

    opened_at = db.Column(db.DateTime, default=datetime.utcnow)
    closed_at = db.Column(db.DateTime, nullable=False)
