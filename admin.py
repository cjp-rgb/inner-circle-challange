"""Admin-side: the live status card that pings on start and edits as the user progresses."""
from telegram.constants import ParseMode
import db as DB
import messages as CP
import config as C

def _name_line(row):
    name = row["name"] or "unnamed yet"
    uname = f"@{row['username']}" if row["username"] else "(no @)"
    return f"👤 {name}  {uname}"

def status_text(row):
    step = row["step"]
    label = DB.STEP_LABEL.get(step, step)
    route = {"new": "New signup", "existing": "Transfer"}.get(row["route"] or "", "—")
    # emoji by stage
    icon = "🟢"
    if step == DB.STEP_CLAIMED: icon = "🟡"
    elif step == DB.STEP_APPROVED: icon = "✅"
    elif step == DB.STEP_REJECTED: icon = "⛔"
    lines = [
        f"{icon} *Onboarding — {label}*",
        _name_line(row),
        f"🆔 tg: `{row['user_id']}`",
        f"Route: {route}",
    ]
    if row["uid"]:
        lines.append(f"💳 *Vantage UID: `{row['uid']}`*  ← verify deposit")
    if step == DB.STEP_CLAIMED:
        lines.append("\n➡️ *Check this UID funded ≥ min, then Approve.*")
    return "\n".join(lines)

async def push_or_update(app, db, user_id):
    """Create the admin status card on first call; edit it on later calls."""
    row = await db.get(user_id)
    if not row:
        return
    text = status_text(row)
    kb = CP.kb_admin_actions(user_id, row["username"])
    msg_id = row["admin_msg_id"]
    if msg_id:
        try:
            await app.bot.edit_message_text(
                chat_id=C.ADMIN_GROUP_ID, message_id=msg_id,
                text=text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb,
                disable_web_page_preview=True,
            )
            return
        except Exception:
            pass  # fall through to send a fresh one
    sent = await app.bot.send_message(
        chat_id=C.ADMIN_GROUP_ID, text=text,
        parse_mode=ParseMode.MARKDOWN, reply_markup=kb, disable_web_page_preview=True,
    )
    await db.set_admin_msg(user_id, sent.message_id)

async def alert_completion(app, db, user_id):
    """Extra ping when they claim done (so it's not missed in the edited thread)."""
    row = await db.get(user_id)
    if not row:
        return
    name = row["name"] or "Someone"
    uname = f"@{row['username']}" if row["username"] else ""
    route = {"new": "new signup", "existing": "transfer"}.get(row["route"] or "", "")
    uid_line = f"\n💳 Vantage UID: `{row['uid']}`" if row["uid"] else ""
    await app.bot.send_message(
        chat_id=C.ADMIN_GROUP_ID,
        text=(f"🟡 *ACTION NEEDED* — {name} {uname} finished onboarding ({route}).{uid_line}\n"
              f"Verify the deposit on that UID, then approve. `/approve {user_id}`"),
        parse_mode=ParseMode.MARKDOWN,
    )
