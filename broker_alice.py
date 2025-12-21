# broker_alice.py
from pya3 import Aliceblue
from models import db, BrokerConnection, StrategyConfig, Trade
from flask_login import current_user
from datetime import datetime

class AliceBroker:
    def __init__(self):
        self.alice = None
        self.conn = None

    def connect(self):
        self.conn = BrokerConnection.query.filter_by(user_id=current_user.id).first()
        if not self.conn or self.conn.paper_trade or not self.conn.api_key:
            return False
        
        try:
            self.alice = Aliceblue(
                user_id=current_user.email,
                api_key=self.conn.api_key,
                session_id=self.conn.session_id
            )
            return True
        except:
            return False

    def place_option_order(self, strategy_name, symbol, side, qty):
        """Place BUY/SELL order. Returns order_id or None if paper/simulated."""
        if not self.alice:
            if self.conn and self.conn.paper_trade:
                print(f"[PAPER] {side} {qty} {symbol}")
                return "PAPER_" + str(datetime.now().timestamp())
            return None

        # LIVE ORDER (adapt to your pya3 version)
        try:
            order_params = {
                "transaction_type": "B" if side == "BUY" else "S",
                "exchange": "NFO",
                "symbol": symbol,
                "instrument": symbol,  # get from alice.get_instrument()
                "quantity": qty * 15,  # BankNifty lot size
                "order_type": "MARKET",
                "product_type": "I",  # Intraday
                "price": 0
            }
            order_id = self.alice.place_order(order_params)
            print(f"[LIVE] {side} {qty} {symbol} order_id={order_id}")
            return order_id
        except Exception as e:
            print(f"Order failed: {e}")
            return None

    def record_trade(self, strategy_name, symbol, side, qty, entry_price, exit_price, pnl):
        """Log completed trade to DB for reports."""
        trade = Trade(
            user_id=current_user.id,
            strategy_name=strategy_name,
            symbol=symbol,
            side=side,
            qty=qty,
            entry_price=entry_price,
            exit_price=exit_price,
            pnl=pnl,
            closed_at=datetime.utcnow()
        )
        db.session.add(trade)
        db.session.commit()
