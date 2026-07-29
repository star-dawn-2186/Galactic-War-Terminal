import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN")

# Discord message links
ACECON_MSG_LINK = 'https://discord.com/channels/1261556132640456764/1427786162272997526/1430116186967904427'
ADVISORY_LINK = 'https://discord.com/channels/1261556132640456764/1427786162272997526'

# Role / User IDs
LEADER_ROLE_ID = 1372466615798726707
OWNER_ID = 803676742639550544  # joe

# Channel IDs
HQ_CHANNEL = 1369361948336062685
LOUNGE_CHANNEL = 1427787543394385930
LAB_CHANNEL = 1439653037554798612
ADVISORY_CHANNEL = 1427786162272997526
HANGOUT_CHANNEL = 1386338755882913906
NEWS_CHANNEL = 1379181040731422822

# ---------------------------------------------------------------------------
# Data output directories
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
LIBERATION_DIR = 'liberation'
EVENTS_DIR = 'events'
ML_DIR = 'ml'


def ensure_data_dirs():
    """Create data output directories if they don't exist."""
    os.makedirs('liberation', exist_ok=True)
    os.makedirs('events', exist_ok=True)
    os.makedirs('ml', exist_ok=True)
