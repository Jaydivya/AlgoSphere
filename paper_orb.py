import os
import time
from datetime import datetime, time as dtime
from dhanhq import dhanhq
from app import app, db, PaperTrade  # reuse Flask DB models

CLIENT_ID = os.environ["DHAN_CLIENT_ID"]
ACCESS_TOKEN = os.environ["DHAN_ACCESS_TOKEN"]

dhan = dhanhq(client_id=CLIENT_ID, access_token=ACCESS_TOKEN)

EXCHANGE_SEGMENT = "NSE_FNO"     # BANKNIFTY options
INDEX_SEGMENT = "NSE_INDEX"     # BANKNIFTY index
INDEX_SECURITY_ID = 25          # BANKNIFTY index security_id from CSV

# TODO: set these to real ATM CE/PE security_ids for today
ATM_CALL_SECURITY_ID = "CE_SECURITY_ID"
ATM_PUT_SECURITY_ID = "PE_SECURITY_ID"

LOT_SIZE = 15
ENTRY_LOTS = 1
TARGET_PTS = 80
STOP_PTS = 50

ORB_START = dtime(9, 15)
ORB_END = dtime(9, 20)
TRADE_START = dtime(9, 20)
TRADE_END = dtime(10, 0)

def get_index_ltp():
    resp = dhan.get_quote(INDEX_SEGMENT, INDEX_SECURITY_ID)
    return float(resp["ltp"])

def get_option_ltp(sec_id):
    resp = dhan.get_quote(EXCHANGE_SEGMENT, sec_id)
    return float(resp["ltp"])

def now_ist():
    return datetime.now()

def in_range(dt, start, end):
    return start <= dt.time() <= end

def main():
    print("Starting BANKNIFTY ORB paper-trade engine...")
    or_high = None
    or_low = None
    in_position = False
    side = None
    entry_price = None
    entry_time = None
    trade_id = None

    while True:
        ts = now_ist()
        t = ts.time()

        try:
            idx_ltp = get_index_ltp()
        except Exception as e:
            print("Index LTP error:", e)
            time.sleep(1)
            continue

        # Build opening range
        if ORB_START <= t < ORB_END:
            or_high = max(or_high or idx_ltp, idx_ltp)
            or_low = min(or_low or idx_ltp, idx_ltp)
            print(f"{ts} ORB | LTP={idx_ltp} | H={or_high} L={or_low}")
            time.sleep(5)
            continue

        # Look for breakout
        if in_range(ts, TRADE_START, TRADE_END) and or_high and or_low and not in_position:
            if idx_ltp > or_high:
                side = "CE"
                opt_id = ATM_CALL_SECURITY_ID
            elif idx_ltp < or_low:
                side = "PE"
                opt_id = ATM_PUT_SECURITY_ID
            else:
                time.sleep(2)
                continue

            entry_price = get_option_ltp(opt_id)
            in_position = True
            entry_time = ts

            with app.app_context():
                trade = PaperTrade(
                    symbol="BANKNIFTY",
                    side=side,
                    qty=ENTRY_LOTS * LOT_SIZE,
                    entry_price=entry_price,
                    entry_time=str(ts),
                    status="OPEN",
                )
                db.session.add(trade)
                db.session.commit()
                trade_id = trade.id

            print(f"{ts} PAPER ENTRY {side} @ {entry_price} (id={trade_id})")

        # Manage open paper trade
        if in_position and trade_id is not None:
            opt_id = ATM_CALL_SECURITY_ID if side == "CE" else ATM_PUT_SECURITY_ID
            try:
                ltp = get_option_ltp(opt_id)
            except Exception as e:
                print("Option LTP error:", e)
                time.sleep(1)
                continue

            pnl_pts = (ltp - entry_price) if side == "CE" else (entry_price - ltp)
            pnl_rs = pnl_pts * LOT_SIZE * ENTRY_LOTS
            print(f"{ts} {side} PAPER PNL {pnl_pts:.1f} pts (~₹{pnl_rs:.0f})")

            exit_reason = None
            if pnl_pts >= TARGET_PTS:
                exit_reason = "TARGET"
            elif pnl_pts <= -STOP_PTS:
                exit_reason = "STOP"
            elif t > TRADE_END:
                exit_reason = "TIME"

            if exit_reason:
                with app.app_context():
                    trade = PaperTrade.query.get(trade_id)
                    if trade:
                        trade.exit_price = ltp
                        trade.exit_time = str(ts)
                        trade.pnl_points = pnl_pts
                        trade.pnl_rupees = pnl_rs
                        trade.status = f"CLOSED_{exit_reason}"
                        db.session.commit()

                print(f"{ts} PAPER EXIT {exit_reason} {pnl_pts:.1f} pts (~₹{pnl_rs:.0f})")
                in_position = False
                trade_id = None

        time.sleep(2)

if __name__ == "__main__":
    main()
