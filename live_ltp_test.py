from pya3 import Aliceblue

USER_ID = "896533"           # your client code
API_KEY = "axZmd91XetUImu5G1nLs7q7ntl2yohUff0o6VHgYv47qeGYVLltj6aKq0xVux9bqyfUtioHichHU7oSWJWuqbYOkGXTyWThZ5o4VF3LgGAIiQzThpPlPblzMFxAsxf3G"  # the long key from AliceBlue API page

print("Connecting...")
alice = Aliceblue(user_id=USER_ID, api_key=API_KEY)
sid = alice.get_session_id()
print("Session ID:", sid)

print("Getting instruments...")
nifty_inst = alice.get_instrument_by_symbol("INDICES", "NIFTY 50")
bank_inst = alice.get_instrument_by_symbol("INDICES", "NIFTY BANK")
print(nifty_inst, bank_inst)

print("Getting quotes...")
nifty_q = alice.get_scrip_info(nifty_inst)
bank_q = alice.get_scrip_info(bank_inst)
print("NIFTY:", nifty_q)
print("BANKNIFTY:", bank_q)

print("LTP NIFTY:", nifty_q.get("Ltp"))
print("LTP BANKNIFTY:", bank_q.get("Ltp"))
