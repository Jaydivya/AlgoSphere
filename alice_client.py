# alice_client.py
from pya3 import Aliceblue

# Read your credentials from safe files / env
USERNAME = open('username.txt').read().strip()
API_KEY  = open('api_key.txt').read().strip()

alice = Aliceblue(user_id=USERNAME, api_key=API_KEY)

# Get and cache session id (do this once per process start)
sid = alice.get_session_id()
print("AliceBlue session:", sid["sessionID"])

def get_index_ltp():
    """Return (nifty_ltp, banknifty_ltp) as floats."""
    # Ensure index contracts are downloaded at least once
    # alice.get_contract_master("INDICES")  # heavy; call manually when needed

    nifty_inst = alice.get_instrument_by_symbol("INDICES", "NIFTY 50")
    bank_inst  = alice.get_instrument_by_symbol("INDICES", "NIFTY BANK")

    nifty_q = alice.get_scrip_info(nifty_inst)
    bank_q  = alice.get_scrip_info(bank_inst)

    return float(nifty_q["Ltp"]), float(bank_q["Ltp"])
