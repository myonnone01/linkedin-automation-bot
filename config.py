"""Configuration loaded from .env."""
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).parent.resolve()
load_dotenv(ROOT / ".env")

# LinkedIn
LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL", "")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD", "")

# Anthropic
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

# Flask
FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))

# Safety caps
DAILY_LIMIT = int(os.getenv("DAILY_LIMIT", "20"))
SESSION_MAX_ACTIONS = int(os.getenv("SESSION_MAX_ACTIONS", "25"))
MIN_CLICK_DELAY_SEC = float(os.getenv("MIN_CLICK_DELAY_SEC", "3"))
MAX_CLICK_DELAY_SEC = float(os.getenv("MAX_CLICK_DELAY_SEC", "8"))
MIN_PROFILE_DELAY_SEC = float(os.getenv("MIN_PROFILE_DELAY_SEC", "30"))
MAX_PROFILE_DELAY_SEC = float(os.getenv("MAX_PROFILE_DELAY_SEC", "60"))

# Paths
DB_PATH = ROOT / "data.db"
PW_PROFILE_DIR = ROOT / ".pw_profile"

# Character limits (LinkedIn-enforced)
CONNECTION_NOTE_LIMIT = 500
INMAIL_LIMIT = 1900
LINKEDIN_MESSAGE_LIMIT = 8000  # generous, LinkedIn allows ~8k

# Delivery methods
DELIVERY_CONNECT_NO_NOTE = "connect_no_note"
DELIVERY_CONNECTION_NOTE = "connection_note"
DELIVERY_LINKEDIN_MESSAGE = "linkedin_message"
DELIVERY_INMAIL = "inmail"

DELIVERY_METHODS = [
    DELIVERY_CONNECT_NO_NOTE,
    DELIVERY_CONNECTION_NOTE,
    DELIVERY_LINKEDIN_MESSAGE,
    DELIVERY_INMAIL,
]

DELIVERY_CHAR_LIMITS = {
    DELIVERY_CONNECT_NO_NOTE: 0,
    DELIVERY_CONNECTION_NOTE: CONNECTION_NOTE_LIMIT,
    DELIVERY_LINKEDIN_MESSAGE: LINKEDIN_MESSAGE_LIMIT,
    DELIVERY_INMAIL: INMAIL_LIMIT,
}

# Claude system prompt (exact text from spec)
CLAUDE_SYSTEM_PROMPT = (
    "You are Mike, an Account Manager at Presidio, a technology solutions "
    "provider specializing in IT infrastructure, cybersecurity, cloud, and "
    "managed services. Write outreach messages that are concise, human, and "
    "relevant to the contact's role, company, and any available signals. "
    "Never sound like a bot. Always lead with relevance, not a pitch."
)
