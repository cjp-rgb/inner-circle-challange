"""The Inner Circle Challenge — onboarding bot. Flat structure, Railway-ready."""
import logging, time
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler,
    ContextTypes, filters,
)

import config as C
import db as DB
import messages as CP
import admin as ADMIN

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("onboard")

db = DB.DB(C.DB_PATH)
VIDEO_KEY = "welcome_video_file_id"


# ---------------- helpers ----------------
async def send_welcome_video(context, chat_id):
    file_id = await db.get_setting(VIDEO_KEY, C.WELCOME_VIDEO_FILE_ID)
    if not file_id:
        return False
    try:
        # video notes are round; if a normal video was set, fall back to send_video
        await context.bot.send_video_note(chat_id=chat_id, video_note=file_id)
        return True
    except Exception:
        try:
            await context.bot.send_video(chat_id=chat_id, video=file_id)
            return True
        except Exception as e:
            log.warning("welcome video failed: %s", e)
            return False


def user_name(row, update):
    if row and row["name"]:
        return row["name"]
    return update.effective_user.first_name or "there"


# ---------------- user flow ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    await db.upsert_start(u.id, u.username or "")
    await db.reset_nudges(u.id)
    # welcome text
    await update.message.reply_text(CP.WELCOME, parse_mode=ParseMode.MARKDOWN)
    # video note
    await send_welcome_video(context, update.effective_chat.id)
    # body + CTA
    await update.message.reply_text(
        CP.welcome_body(), parse_mode=ParseMode.MARKDOWN, reply_markup=CP.kb_welcome(),
        disable_web_page_preview=True,
    )
    # ping admin (creates the status card)
    await ADMIN.push_or_update(context.application, db, u.id)


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data
    uid = q.from_user.id

    # admin approve/reject (pressed in admin group)
    if data.startswith("approve:") or data.startswith("reject:"):
        target = int(data.split(":")[1])
        await _do_decision(context, target, approve=data.startswith("approve:"))
        return

    row = await db.get(uid)

    if data == "go":
        await db.set_step(uid, DB.STEP_STARTED)
        await db.reset_nudges(uid)
        await context.bot.send_message(uid, CP.ASK_NAME)
        context.user_data["awaiting_name"] = True
        await ADMIN.push_or_update(context.application, db, uid)

    elif data == "question":
        name = row["name"] if row else ""
        await context.bot.send_message(
            uid, CP.question_msg(name), reply_markup=CP.kb_message_carson()
        )

    elif data == "route_new":
        await db.set_route(uid, "new")
        await db.reset_nudges(uid)
        name = user_name(row, update)
        await context.bot.send_message(
            uid, CP.instructions_new(name), parse_mode=ParseMode.MARKDOWN,
            reply_markup=CP.kb_new_done(), disable_web_page_preview=True,
        )
        await db.set_step(uid, DB.STEP_INSTRUCTED)
        await ADMIN.push_or_update(context.application, db, uid)

    elif data == "route_existing":
        await db.set_route(uid, "existing")
        await db.reset_nudges(uid)
        name = user_name(row, update)
        await context.bot.send_message(
            uid, CP.instructions_transfer(name), parse_mode=ParseMode.MARKDOWN,
            reply_markup=CP.kb_transfer_done(), disable_web_page_preview=True,
        )
        await db.set_step(uid, DB.STEP_INSTRUCTED)
        await ADMIN.push_or_update(context.application, db, uid)

    elif data == "finish":
        # they've signed up / requested transfer — now collect UID
        await db.set_step(uid, DB.STEP_AWAIT_UID)
        await db.reset_nudges(uid)
        name = user_name(row, update)
        await context.bot.send_message(
            uid, CP.ask_uid(name), parse_mode=ParseMode.MARKDOWN,
            reply_markup=CP.kb_uid_stuck(), disable_web_page_preview=True,
        )
        context.user_data["awaiting_uid"] = True
        await ADMIN.push_or_update(context.application, db, uid)


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = (update.message.text or "").strip()

    # --- capturing UID ---
    if context.user_data.get("awaiting_uid"):
        digits = "".join(ch for ch in text if ch.isdigit())
        if len(digits) < 5 or len(digits) > 12:
            await update.message.reply_text(
                CP.uid_invalid(), reply_markup=CP.kb_uid_stuck()
            )
            return
        await db.set_uid(uid, digits)
        context.user_data["awaiting_uid"] = False
        await db.reset_nudges(uid)
        row = await db.get(uid)
        name = row["name"] or "there"
        await update.message.reply_text(
            CP.claimed_ack(name), parse_mode=ParseMode.MARKDOWN,
            reply_markup=CP.kb_after_claim(),
        )
        await ADMIN.push_or_update(context.application, db, uid)
        await ADMIN.alert_completion(context.application, db, uid)
        return

    # --- capturing name ---
    if context.user_data.get("awaiting_name"):
        name = text[:40]
        if not name:
            await update.message.reply_text("Just pop your name in 👇")
            return
        await db.set_name(uid, name)
        context.user_data["awaiting_name"] = False
        await update.message.reply_text(
            CP.route_question(name), parse_mode=ParseMode.MARKDOWN, reply_markup=CP.kb_route()
        )
        await ADMIN.push_or_update(context.application, db, uid)
        return


# ---------------- approval ----------------
async def _do_decision(context, target_id, approve):
    row = await db.get(target_id)
    if not row:
        return
    name = row["name"] or "there"
    if approve:
        await db.set_step(target_id, DB.STEP_APPROVED)
        try:
            await context.bot.send_message(
                target_id, CP.approved_msg(name), parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True,
            )
        except Exception as e:
            log.warning("could not DM approved user %s: %s", target_id, e)
    else:
        await db.set_step(target_id, DB.STEP_REJECTED)
        try:
            await context.bot.send_message(
                target_id, CP.rejected_msg(name), reply_markup=CP.kb_message_carson()
            )
        except Exception:
            pass
    await ADMIN.push_or_update(context.application, db, target_id)


# ---------------- admin commands ----------------
def _is_admin(update):
    return update.effective_user and update.effective_user.id == C.ADMIN_USER_ID

async def cmd_approve(update, context):
    if not _is_admin(update): return
    if not context.args:
        await update.message.reply_text("Usage: /approve <user_id>")
        return
    await _do_decision(context, int(context.args[0]), approve=True)
    await update.message.reply_text("✅ Approved.")

async def cmd_reject(update, context):
    if not _is_admin(update): return
    if not context.args:
        await update.message.reply_text("Usage: /reject <user_id>")
        return
    await _do_decision(context, int(context.args[0]), approve=False)
    await update.message.reply_text("⛔ Rejected.")

async def cmd_stats(update, context):
    if not _is_admin(update): return
    s = await db.stats()
    order = [DB.STEP_STARTED, DB.STEP_NAMED, DB.STEP_ROUTED, DB.STEP_INSTRUCTED,
             DB.STEP_CLAIMED, DB.STEP_APPROVED, DB.STEP_REJECTED]
    lines = ["📊 *Onboarding funnel*"]
    for st in order:
        lines.append(f"• {DB.STEP_LABEL[st]}: *{s.get(st,0)}*")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)

async def cmd_pending(update, context):
    if not _is_admin(update): return
    rows = await db.pending()
    if not rows:
        await update.message.reply_text("Nothing awaiting approval 🎉")
        return
    for r in rows:
        await update.message.reply_text(
            ADMIN.status_text(r), parse_mode=ParseMode.MARKDOWN,
            reply_markup=CP.kb_admin_actions(r["user_id"], r["username"]),
        )

async def cmd_find(update, context):
    if not _is_admin(update): return
    if not context.args:
        await update.message.reply_text("Usage: /find <name or @username>")
        return
    term = " ".join(context.args).lstrip("@")
    rows = await db.find_by_name(term)
    if not rows:
        await update.message.reply_text("No matches.")
        return
    for r in rows[:8]:
        await update.message.reply_text(
            ADMIN.status_text(r), parse_mode=ParseMode.MARKDOWN,
            reply_markup=CP.kb_admin_actions(r["user_id"], r["username"]),
        )

async def cmd_setvideo(update, context):
    if not _is_admin(update): return
    msg = update.message.reply_to_message
    if not msg or not (msg.video_note or msg.video):
        await update.message.reply_text(
            "Reply to a *video note* (or video) with /setvideo to set the welcome clip.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    file_id = msg.video_note.file_id if msg.video_note else msg.video.file_id
    await db.set_setting(VIDEO_KEY, file_id)
    await update.message.reply_text("✅ Welcome video set. New joiners will see it on /start.")

async def cmd_help(update, context):
    if not _is_admin(update): return
    await update.message.reply_text(
        "*Admin commands*\n"
        "/setvideo — reply to a video note to set the welcome clip\n"
        "/stats — funnel counts\n"
        "/pending — everyone awaiting approval\n"
        "/find <name|@user> — look someone up + act\n"
        "/approve <id> · /reject <id>",
        parse_mode=ParseMode.MARKDOWN,
    )


# ---------------- nudges ----------------
async def nudge_job(context: ContextTypes.DEFAULT_TYPE):
    now = time.time()
    rows = await db.stalled()
    for r in rows:
        # never nudge people who already completed/approved/rejected (stalled() excludes them)
        # skip users who haven't even chosen a route unless they at least started
        hours_since = (now - r["updated_at"]) / 3600.0
        sent = set(filter(None, (r["nudges_sent"] or "").split(",")))
        for h in C.NUDGE_HOURS:
            if hours_since >= h and str(h) not in sent and str(int(h)) not in sent:
                await _send_nudge(context, r, int(h) if h == int(h) else h)
                await db.mark_nudge(r["user_id"], int(h) if h == int(h) else h)
                break  # one nudge per cycle per user

async def _send_nudge(context, row, hour):
    name = row["name"] or "there"
    fn = CP.NUDGE_BY_HOUR.get(int(hour))
    if not fn:
        # nearest defined
        fn = CP.NUDGE_BY_HOUR.get(sorted(CP.NUDGE_BY_HOUR)[-1])
    try:
        await context.bot.send_message(
            row["user_id"], fn(name), reply_markup=CP.kb_continue()
        )
    except Exception as e:
        log.info("nudge to %s failed: %s", row["user_id"], e)


# ---------------- lifecycle ----------------
async def post_init(app):
    await db.connect()
    log.info("Onboarding bot initialised. admin_group=%s", C.ADMIN_GROUP_ID)

def main():
    app = Application.builder().token(C.BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setvideo", cmd_setvideo))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("pending", cmd_pending))
    app.add_handler(CommandHandler("find", cmd_find))
    app.add_handler(CommandHandler("approve", cmd_approve))
    app.add_handler(CommandHandler("reject", cmd_reject))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    # nudge check every 15 min
    app.job_queue.run_repeating(nudge_job, interval=900, first=120)

    log.info("Starting onboarding bot…")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
