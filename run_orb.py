# file: run_orb.py
import os
from dhanhq import DhanContext, MarketFeed

# ========= ENV CONFIG =========
CLIENT_ID = os.environ["DHAN_CLIENT_ID"]       # e.g. "1100734437"
ACCESS_TOKEN = os.environ["DHAN_ACCESS_TOKEN"] # 24-hr token

print("PY CLIENT_ID:", CLIENT_ID)
print("PY TOKEN   :", ACCESS_TOKEN[:20] + "...")

# Create context
dhan_context = DhanContext(CLIENT_ID, ACCESS_TOKEN)

# ========= INSTRUMENTS (v2) =========
# Use NSE as per DhanHQ-py docs; library maps it to proper segments internally. [web:229][web:288]
# Replace "13" and "25" with your NIFTY and BANKNIFTY security_ids as needed.
instruments = [
    (MarketFeed.NSE, "13", MarketFeed.Ticker),   # NIFTY index ticker
    (MarketFeed.NSE, "25", MarketFeed.Ticker),   # BANKNIFTY index ticker
]

version = "v2"

try:
    data = MarketFeed(dhan_context, instruments, version)
    print("Connecting MarketFeed v2...")
    while True:
        data.run_forever()          # maintain connection
        response = data.get_data()  # get latest batch

        # response is usually a list of dicts
        if isinstance(response, list):
            for tick in response:
                print(tick)
        else:
            print(response)

except Exception as e:
    print("MarketFeed error:", e)
