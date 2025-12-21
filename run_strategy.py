# run_strategy.py - Run this separately for live trading
from apscheduler.schedulers.background import BackgroundScheduler
from strategies.banknifty_orb_vwap import BankNiftyORB
from pya3 import Aliceblue

scheduler = BackgroundScheduler()
strategy = BankNiftyORB()

def tick_loop():
    """Fetch BankNifty LTP every second during market hours."""
    if strategy.broker.connect():
        ltp_data = strategy.broker.alice.get_ltp("NSE", "NIFTY BANK")
        strategy.on_tick("BANKNIFTY", ltp_data["ltp"], ltp_data.get("volume", 0))

scheduler.add_job(tick_loop, "interval", seconds=5)  # 5-sec ticks
scheduler.start()

print("Live trading started. Press Ctrl+C to stop.")
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    scheduler.shutdown()
