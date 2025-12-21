# strategies/banknifty_orb_vwap.py
import time
from datetime import datetime, time as dt_time
from broker_alice import AliceBroker

class BankNiftyORB:
    def __init__(self):
        self.broker = AliceBroker()
        self.or_high = 0
        self.or_low = 0
        self.vwap = 0
        self.position = None  # {'symbol':, 'side':, 'qty':, 'entry_price':}
        self.daily_pnl = 0
        self.orb_start = dt_time(9, 15)  # 09:15 IST
        self.orb_end = dt_time(9, 20)
        self.trade_end = dt_time(10, 0)

    def is_trading_time(self):
        now = datetime.now().time()
        return self.orb_start <= now <= self.trade_end

    def on_tick(self, symbol, ltp, volume):
        """Called on every BankNifty spot tick."""
        now = datetime.now().time()

        # 1) Mark ORB range (09:15-09:20)
        if self.orb_start <= now <= self.orb_end:
            self.or_high = max(self.or_high, ltp)
            self.or_low = min(self.or_low, ltp) if self.or_low else ltp
            self.vwap = (self.vwap * 0.9 + ltp * 0.1)  # rolling VWAP

        # 2) Entry signals (09:20-10:00)
        elif self.is_trading_time() and not self.position:
            config = StrategyConfig.query.filter_by(
                user_id=current_user.id, strategy_name="banknifty_orb_vwap"
            ).first()
            if not config or not config.enabled:
                return

            lots = config.lots
            avg_vol = 1000  # TODO: track 5-min avg volume

            # BUY CE signal
            if ltp > self.or_high and ltp > self.vwap and volume > avg_vol:
                atm_strike = round(ltp / 100) * 100  # snap to strike
                ce_symbol = f"BANKNIFTY{datetime.now().strftime('%y%b%d')}{atm_strike}CE"
                
                order_id = self.broker.place_option_order(
                    "banknifty_orb_vwap", ce_symbol, "BUY", lots
                )
                if order_id:
                    self.position = {
                        "symbol": ce_symbol, "side": "BUY", "qty": lots,
                        "entry_price": ltp * 0.8  # assume option premium ~80% spot move
                    }

            # SELL PE signal (symmetric)
            elif ltp < self.or_low and ltp < self.vwap and volume > avg_vol:
                atm_strike = round(ltp / 100) * 100
                pe_symbol = f"BANKNIFTY{datetime.now().strftime('%y%b%d')}{atm_strike}PE"
                
                order_id = self.broker.place_option_order(
                    "banknifty_orb_vwap", pe_symbol, "BUY", lots
                )
                if order_id:
                    self.position = {
                        "symbol": pe_symbol, "side": "BUY", "qty": lots,
                        "entry_price": ltp * 0.8
                    }

        # 3) Manage exits
        if self.position:
            config = StrategyConfig.query.filter_by(
                user_id=current_user.id, strategy_name="banknifty_orb_vwap"
            ).first()
            
            option_pnl_points = (ltp - self.position["entry_price"]) * 1.25  # option multiplier
            
            # Target hit
            if option_pnl_points >= config.target_points:
                exit_price = ltp * 0.8
                pnl = (exit_price - self.position["entry_price"]) * self.position["qty"]
                self.broker.record_trade(
                    "banknifty_orb_vwap", self.position["symbol"],
                    self.position["side"], self.position["qty"],
                    self.position["entry_price"], exit_price, pnl
                )
                self.position = None
                self.daily_pnl += pnl

            # Stop loss
            elif option_pnl_points <= -config.stop_points or self.daily_pnl <= -config.daily_max_loss:
                exit_price = ltp * 0.8
                pnl = (exit_price - self.position["entry_price"]) * self.position["qty"]
                self.broker.record_trade(...)  # same as above
                self.position = None
                self.daily_pnl += pnl
