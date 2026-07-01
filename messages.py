"""All user-facing copy + keyboards. Edit text here."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import config as C

def _carson_url():
    return f"https://t.me/{C.CARSON_HANDLE}"

# ---------- keyboards ----------
def kb_welcome():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Let's go 🚀", callback_data="go")],
        [InlineKeyboardButton("I've got a question", callback_data="question")],
    ])

def kb_route():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("I'm new to trading", callback_data="route_new")],
        [InlineKeyboardButton("I already have a Vantage live trading account", callback_data="route_existing")],
    ])

def kb_new_done():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ I've signed up", callback_data="finish")],
        [InlineKeyboardButton("I've got a question", callback_data="question")],
    ])

def kb_transfer_done():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ I've requested the transfer", callback_data="finish")],
        [InlineKeyboardButton("Message Carson", url=_carson_url())],
    ])

def kb_uid_stuck():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Can't find it? Message Carson", url=_carson_url())],
    ])

def kb_after_claim():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Message Carson", url=_carson_url())],
    ])

def kb_message_carson():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Message Carson", url=_carson_url())],
    ])

def kb_continue():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Continue ▶️", callback_data="go")],
    ])

def kb_admin_actions(user_id, username):
    row = [InlineKeyboardButton("✅ Approve", callback_data=f"approve:{user_id}"),
           InlineKeyboardButton("❌ Reject", callback_data=f"reject:{user_id}")]
    row2 = []
    if username:
        row2.append(InlineKeyboardButton("💬 Message them", url=f"https://t.me/{username}"))
    return InlineKeyboardMarkup([row, row2] if row2 else [row])

# ---------- user messages ----------
WELCOME = (
    "👋 Welcome to *The Inner Circle Challenge*.\n\n"
    "You're seconds away from your place in the first cohort. "
    "Before anything else — watch this 👇"
)

def welcome_body():
    return (
        "Here's the short version:\n\n"
        "🔹 A 6-week live trading challenge\n"
        "🔹 Daily signals, live weekly calls, a full framework\n"
        "🔹 A *$1,000+ prize pool* — won by the most disciplined trader\n"
        f"🔹 Free to enter — you fund your own account (minimum *{C.MIN_DEPOSIT}*), and your capital stays yours\n\n"
        "Whether you've traded for years or never placed a trade, you get a Starter Playbook covering everything.\n\n"
        "Ready to lock in your place? 👇"
    )

ASK_NAME = "Perfect. First — what's your name? (Just so we know who you are 👊)"

def route_question(name):
    return (
        f"Nice to meet you, {name} 🤝\n\n"
        "Quick one so I point you the right way 👇"
    )

def instructions_new(name):
    return (
        f"Easy, {name} — I'll walk you through it 👇\n\n"
        f"*1.* Open your account here:\n{C.VANTAGE_LINK}\n\n"
        "*2.* ✅ Tick *both* boxes and hit proceed — *we don't use the other version*\n\n"
        "*3.* Choose a *Standard STP account*\n\n"
        f"*4.* Fund it with a minimum of *{C.MIN_DEPOSIT}* — your money, stays yours\n\n"
        f"⏳ You've got until *{C.DEADLINE_TEXT}* to fund your account — don't leave it too late. "
        "If you're not funded yet, get it sorted before the window closes.\n\n"
        "Signed up? Tap below to finish 👇"
    )

def instructions_transfer(name):
    return (
        f"No problem, {name} — you can move your existing account under the challenge so you're eligible 👇\n\n"
        "*1.* Log in to your *Vantage dashboard*\n"
        "*2.* Go to *Transfer IB / CPA Affiliate*\n"
        f"*3.* Enter code: *{C.IB_CODE}*\n"
        f"*4.* Name: *{C.IB_NAME}*\n"
        "*5.* Submit the request\n\n"
        f"Then make sure you're funded with a minimum of *{C.MIN_DEPOSIT}* — and get it done before *{C.DEADLINE_TEXT}*.\n\n"
        "Transfers sometimes need a quick manual check — any snag, just message me.\n\n"
        "Requested it? Tap below to finish 👇"
    )

def ask_uid(name):
    return (
        f"Almost there, {name} 🙌\n\n"
        "Last step — I need your *Vantage account number (UID)* so we can confirm your deposit and get you in.\n\n"
        "📍 *Where to find it:* log in to Vantage → *top left, your profile* → your account number/UID is there.\n\n"
        "Paste it below 👇 (just the number)"
    )

def uid_invalid():
    return (
        "Hmm, that doesn't look like a valid UID — it should be a number (usually 6–9 digits).\n\n"
        "Have another look (Vantage → top left → profile) and paste just the number. "
        "Stuck? Message Carson and he'll help 👇"
    )

def claimed_ack(name):
    return (
        f"Brilliant work, {name} 🙌 you're all set on your end.\n\n"
        "Carson's going to verify your account and deposit, then you'll be let straight into "
        "*The Challenge Room* and *The Social Challenge Room*.\n\n"
        "This usually doesn't take long — you'll get a message here the moment you're approved. 🔥\n\n"
        "Can't wait? Message Carson directly 👇"
    )

def approved_msg(name):
    lines = [f"🎉 You're in, {name}! Welcome to the first cohort.", "", "Your rooms 👇"]
    if C.SIGNALS_INVITE:
        lines.append(f"📊 The Challenge Room (signals): {C.SIGNALS_INVITE}")
    if C.COMMUNITY_INVITE:
        lines.append(f"💬 The Social Challenge Room (community): {C.COMMUNITY_INVITE}")
    lines += ["", "Introduce yourself and get ready — this is where it all happens. See you inside. 🔥"]
    return "\n".join(lines)

def rejected_msg(name):
    return (
        f"Hi {name} — we couldn't confirm your setup just yet. "
        "No worries at all, message Carson and he'll help you get sorted 👇"
    )

def question_msg(name):
    who = f" {name}" if name else ""
    return (
        f"No worries{who} — Carson's happy to help with anything.\n\n"
        "Tap below to message him directly 👇"
    )

# ---------- nudges ----------
def nudge_1h(name):
    return (
        f"Hey {name} 👋 you started getting set up for the Challenge but didn't finish. "
        "You're nearly there — pick up where you left off 👇"
    )

def nudge_8h(name):
    return (
        f"{name}, your spot in the first cohort is still saved 👀 but the cohort starts "
        f"{C.DEADLINE_TEXT} and places are capped. Don't leave it too late 👇"
    )

def nudge_48h(name):
    return (
        f"Last nudge, {name} 🔔 the Challenge kicks off soon and I'd hate for you to miss the first cohort. "
        "Everything's ready when you are — takes 5 minutes 👇\n\n"
        "Any problems at all? Just message Carson, he'll help."
    )

NUDGE_BY_HOUR = {1: nudge_1h, 8: nudge_8h, 48: nudge_48h}
