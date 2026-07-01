"""Configuration — all from environment variables (set in Railway)."""
import os

def _req(name):
    v = os.environ.get(name)
    if not v:
        raise RuntimeError(f"Missing required env var: {name}")
    return v

# --- required ---
BOT_TOKEN = _req("BOT_TOKEN")
ADMIN_GROUP_ID = int(_req("ADMIN_GROUP_ID"))   # chat where you get start/step/completion alerts + approve
ADMIN_USER_ID = int(_req("ADMIN_USER_ID"))     # your personal Telegram user id (for admin cmds in DM)

# --- Vantage ---
VANTAGE_LINK = os.environ.get("VANTAGE_LINK", "https://go.vantagefx.com/visit/?bta=64187&brand=vantagefx")
IB_CODE = os.environ.get("IB_CODE", "64187")
IB_NAME = os.environ.get("IB_NAME", "Carson Pickard")

# --- group invite links handed out on approval ---
SIGNALS_INVITE = os.environ.get("SIGNALS_INVITE", "")     # "The Challenge Room" (signals)
COMMUNITY_INVITE = os.environ.get("COMMUNITY_INVITE", "") # "The Social Challenge Room" (community)

# --- your handle for "Message Carson" buttons (without @) ---
CARSON_HANDLE = os.environ.get("CARSON_HANDLE", "carsonpickardd")

# --- tunables ---
MIN_DEPOSIT = os.environ.get("MIN_DEPOSIT", "£500")
EVENT_NAME = os.environ.get("EVENT_NAME", "The Inner Circle Challenge")
DEADLINE_TEXT = os.environ.get("DEADLINE_TEXT", "Monday")
DB_PATH = os.environ.get("DB_PATH", "/data/onboarding.db")

# nudge timing (hours after last activity if not completed), comma-separated
NUDGE_HOURS = [float(x) for x in os.environ.get("NUDGE_HOURS", "1,8,48").split(",")]

# welcome video note file_id — set at runtime via /setvideo (stored in DB); env is fallback
WELCOME_VIDEO_FILE_ID = os.environ.get("WELCOME_VIDEO_FILE_ID", "")
