# strategies/banknifty_orb_vwap.py
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from collections import deque

@dataclass
class StrategyParams:
    lot_size: int = 3
    target_pts: int = 80
    stop_pts: int = 50
    trade_window_start: time = time(9, 20)
    trade_window_end: time = time(10, 0)

class BankNiftyOrbVwap:
    def __init__(self, params: StrategyParams):
        self.p = params
        self.or_high = None
        self.or_low = None
        self.in_position = False
        self.position_side = None  # "CE" or "PE"
        self.entry_price = None
        self.entry_time = None
        self.vwap_num = 0.0
        self.vwap_den = 0.0
        self.vol_window = deque(maxlen=5)

    def in_orb_window(self, ts: datetime) -> bool:
        return time(9, 15) <= ts.time() < time(9, 20)

    def in_trade_window(self, ts: datetime) -> bool:
        return self.p.trade_window_start <= ts.time() <= self.p.trade_window_end

    def update_vwap_volume(self, price: float, volume: int):
        self.vwap_num += price * volume
        self.vwap_den += volume
        if volume:
            self.vol_window.append(volume)

    @property
    def vwap(self):
        return self.vwap_num / self.vwap_den if self.vwap_den else None

    @property
    def avg_vol(self):
        return sum(self.vol_window) / len(self.vol_window) if self.vol_window else 0

    def on_1min_candle(self, ts: datetime, high: float, low: float,
                       close: float, volume: int):
        self.update_vwap_volume(close, volume)

        if self.in_orb_window(ts):
            self.or_high = max(self.or_high or close, high)
            self.or_low = min(self.or_low or close, low)
            return None

        if not self.in_trade_window(ts):
            return None

        if not self.or_high or not self.or_low or not self.vwap:
            return None

        # volume filter
        if self.avg_vol and volume <= self.avg_vol:
            return None

        signal = None
        if close > self.or_high and close > self.vwap:
            signal = "CE"
        elif close < self.or_low and close < self.vwap:
            signal = "PE"

        return signal  # "CE", "PE", or None

    def on_option_tick(self, ts: datetime, ltp: float):
        if not self.in_position:
            return None

        elapsed = (ts - self.entry_time)
        pnl_pts = ltp - self.entry_price if self.position_side == "CE" else self.entry_price - ltp

        if pnl_pts >= self.p.target_pts:
            return "TARGET_EXIT"
        if pnl_pts <= -self.p.stop_pts:
            return "STOP_EXIT"
        if elapsed >= timedelta(minutes=10):
            return "TIME_EXIT"
        return None

    def enter(self, side: str, price: float, ts: datetime):
        self.in_position = True
        self.position_side = side
        self.entry_price = price
        self.entry_time = ts

    def exit(self):
        self.in_position = False
        self.position_side = None
        self.entry_price = None
        self.entry_time = None
