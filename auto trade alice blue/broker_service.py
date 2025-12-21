# broker_service.py
from flask_login import current_user
from models import db, BrokerConnection
from pya3 import Aliceblue
import traceback


def connect_broker_live(client_id: str, api_key: str, password: str, require_confirm: bool = True):
    """
    Shared helper used by:
      - /broker/connect (require_confirm=True)
      - auto-connect after user login (require_confirm=False)
    Returns (ok: bool, message: str).
    """
    if not all([client_id, api_key, password]):
        return False, "All fields (Client ID, API Key, Password) are required."

    conn = BrokerConnection.query.filter_by(user_id=current_user.id).first()
    if not conn:
        conn = BrokerConnection(user_id=current_user.id, broker="aliceblue")
        db.session.add(conn)

    try:
        print(f"Connecting with client_id={client_id[:4]}...")
        alice = Aliceblue(user_id=client_id, api_key=api_key)
        session_id = alice.get_session_id()

        conn.api_key = api_key
        conn.session_id = session_id
        conn.paper_trade = False  # LIVE MODE
        db.session.commit()
        return True, "LIVE TRADING ENABLED! Real orders will now execute."
    except Exception as e:
        print(f"Broker connect error: {e}")
        print(traceback.format_exc())
        return False, f"Connection failed: {str(e)}"
