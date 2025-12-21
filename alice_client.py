from alice_blue import AliceBlue

# ====== CONFIG: define constants BEFORE get_alice() ======
ALICE_USER_ID = "896533"
ALICE_PASSWORD = "Jaydivya@123"
ALICE_2FA = "1983"

ALICE_APP_ID = "zykfqZhl0jXPfnN"  # short App Code
ALICE_API_SECRET = (
    "eHLpuCqonLMkmCIgIqNTJtDOREINxSBCEIMQiKJvpjCvvmZqbzqKkyZFcLCTJOdFcIZYBlDOJVGcAcyzrxjMLTnCjMmCYCrkhoYI"
)  # long Secret Key

_alice = None

def get_alice() -> AliceBlue:
    global _alice
    if _alice is not None:
        return _alice

    session_id = AliceBlue.login_and_get_sessionID(
        username=ALICE_USER_ID,
        password=ALICE_PASSWORD,
        twoFA=ALICE_2FA,
        app_id=ALICE_APP_ID,
        api_secret=ALICE_API_SECRET,
    )

    _alice = AliceBlue(username=ALICE_USER_ID, session_id=session_id)
    return _alice
