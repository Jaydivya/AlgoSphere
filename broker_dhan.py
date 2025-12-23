# broker_dhan.py
import os
from datetime import datetime
from dhanhq import dhanhq

DHAN_CLIENT_ID = os.environ["DHAN_CLIENT_ID"]
DHAN_ACCESS_TOKEN = os.environ["DHAN_ACCESS_TOKEN"]

dhan = dhanhq(client_id=DHAN_CLIENT_ID, access_token=DHAN_ACCESS_TOKEN)

# TODO: replace with real IDs from your instruments list
BANKNIFTY_SPOT_SECURITY_ID = "BANKNIFTY_INDEX_ID"
EXCHANGE_SEGMENT_SPOT = "NSE_INDEX"
EXCHANGE_SEGMENT_OPT = "NSE_FNO"
STRIKE_STEP = 100  # adjust to Dhan BANKNIFTY strike step

def get_banknifty_spot_ltp():
    q = dhan.get_quote(EXCHANGE_SEGMENT_SPOT, BANKNIFTY_SPOT_SECURITY_ID)
    return float(q["ltp"])

def resolve_atm_option(side: str, expiry: str):
    """
    side: 'CE' or 'PE'
    expiry: 'YYYY-MM-DD' (weekly expiry)
    """
    spot = get_banknifty_spot_ltp()
    atm = round(spot / STRIKE_STEP) * STRIKE_STEP
    # here you map (expiry, atm, side) to security_id using your instruments CSV
    security_id = lookup_option_security_id(expiry, atm, side)
    return security_id, atm

def lookup_option_security_id(expiry: str, strike: int, side: str) -> str:
    # stub – implement using your instruments master (CSV or DB)
    raise NotImplementedError("wire to your Dhan instruments list")
