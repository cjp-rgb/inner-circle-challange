"""SQLite storage for onboarding: user step-state, timestamps, nudges, settings."""
import aiosqlite
import time

# Step constants (ordered) — used for funnel + nudges
STEP_STARTED     = "started"       # hit /start
STEP_AWAIT_NAME  = "await_name"    # tapped Let's go, now typing name
STEP_NAMED       = "named"         # gave name
STEP_ROUTED      = "routed"        # chose new / existing
STEP_INSTRUCTED  = "instructed"    # shown funding / transfer instructions
STEP_AWAIT_UID   = "await_uid"     # tapped finish, now sending UID
STEP_CLAIMED     = "claimed"       # submitted UID -> awaiting your verification
STEP_APPROVED    = "approved"      # you approved -> in the groups
STEP_REJECTED    = "rejected"

STEP_ORDER = [STEP_STARTED, STEP_AWAIT_NAME, STEP_NAMED, STEP_ROUTED, STEP_INSTRUCTED, STEP_AWAIT_UID, STEP_CLAIMED, STEP_APPROVED]

STEP_LABEL = {
    STEP_STARTED: "Started (watched welcome)",
    STEP_AWAIT_NAME: "Entering name",
    STEP_NAMED: "Gave name",
    STEP_ROUTED: "Chose route",
    STEP_INSTRUCTED: "Shown instructions",
    STEP_AWAIT_UID: "Signed up — sending UID",
    STEP_CLAIMED: "UID submitted — verify deposit",
    STEP_APPROVED: "Approved — in groups",
    STEP_REJECTED: "Rejected",
}


class DB:
    def __init__(self, path):
        self.path = path
        self._db = None

    async def connect(self):
        self._db = await aiosqlite.connect(self.path)
        self._db.row_factory = aiosqlite.Row
        await self._db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id       INTEGER PRIMARY KEY,
                username      TEXT,
                name          TEXT,
                route         TEXT,           -- 'new' | 'existing'
                uid           TEXT,           -- Vantage account UID
                step          TEXT NOT NULL DEFAULT 'started',
                admin_msg_id  INTEGER,        -- the admin-chat message we edit as they progress
                nudges_sent   TEXT NOT NULL DEFAULT '',  -- comma list of hours already sent
                created_at    REAL NOT NULL,
                updated_at    REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT
            );
            """
        )
        await self._db.commit()
        await self._migrate()

    async def _migrate(self):
        """Add any columns missing from an older existing database (CREATE TABLE
        IF NOT EXISTS won't add columns to a table that already exists)."""
        cur = await self._db.execute("PRAGMA table_info(users)")
        cols = {row["name"] for row in await cur.fetchall()}
        wanted = {
            "username": "TEXT",
            "name": "TEXT",
            "route": "TEXT",
            "uid": "TEXT",
            "step": "TEXT NOT NULL DEFAULT 'started'",
            "admin_msg_id": "INTEGER",
            "nudges_sent": "TEXT NOT NULL DEFAULT ''",
        }
        for col, decl in wanted.items():
            if col not in cols:
                # SQLite can't add NOT NULL without default retroactively; strip if needed
                safe_decl = decl
                await self._db.execute(f"ALTER TABLE users ADD COLUMN {col} {safe_decl}")
        await self._db.commit()

    async def close(self):
        if self._db:
            await self._db.close()

    # ---- settings (welcome video id) ----
    async def set_setting(self, key, value):
        await self._db.execute(
            "INSERT INTO settings(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        await self._db.commit()

    async def get_setting(self, key, default=None):
        cur = await self._db.execute("SELECT value FROM settings WHERE key=?", (key,))
        row = await cur.fetchone()
        return row["value"] if row else default

    # ---- users ----
    async def upsert_start(self, user_id, username):
        now = time.time()
        await self._db.execute(
            """INSERT INTO users(user_id,username,step,created_at,updated_at)
               VALUES(?,?,?,?,?)
               ON CONFLICT(user_id) DO UPDATE SET username=excluded.username, updated_at=excluded.updated_at""",
            (user_id, username or "", STEP_STARTED, now, now),
        )
        await self._db.commit()

    async def get(self, user_id):
        cur = await self._db.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        return await cur.fetchone()

    async def set_name(self, user_id, name):
        await self._db.execute(
            "UPDATE users SET name=?, step=?, updated_at=? WHERE user_id=?",
            (name, STEP_NAMED, time.time(), user_id),
        )
        await self._db.commit()

    async def set_route(self, user_id, route):
        await self._db.execute(
            "UPDATE users SET route=?, step=?, updated_at=? WHERE user_id=?",
            (route, STEP_ROUTED, time.time(), user_id),
        )
        await self._db.commit()

    async def set_uid(self, user_id, uid):
        await self._db.execute(
            "UPDATE users SET uid=?, step=?, updated_at=? WHERE user_id=?",
            (uid, STEP_CLAIMED, time.time(), user_id),
        )
        await self._db.commit()

    async def set_step(self, user_id, step):
        await self._db.execute(
            "UPDATE users SET step=?, updated_at=? WHERE user_id=?",
            (step, time.time(), user_id),
        )
        await self._db.commit()

    async def reset_nudges(self, user_id):
        await self._db.execute(
            "UPDATE users SET nudges_sent='', updated_at=? WHERE user_id=?",
            (time.time(), user_id),
        )
        await self._db.commit()

    async def mark_nudge(self, user_id, hour):
        row = await self.get(user_id)
        sent = set(filter(None, (row["nudges_sent"] or "").split(",")))
        sent.add(str(hour))
        await self._db.execute(
            "UPDATE users SET nudges_sent=? WHERE user_id=?",
            (",".join(sorted(sent, key=float)), user_id),
        )
        await self._db.commit()

    async def set_admin_msg(self, user_id, msg_id):
        await self._db.execute(
            "UPDATE users SET admin_msg_id=? WHERE user_id=?", (msg_id, user_id)
        )
        await self._db.commit()

    # ---- queries ----
    async def pending(self):
        cur = await self._db.execute(
            "SELECT * FROM users WHERE step=? ORDER BY updated_at", (STEP_CLAIMED,)
        )
        return await cur.fetchall()

    async def find_by_name(self, term):
        cur = await self._db.execute(
            "SELECT * FROM users WHERE name LIKE ? OR username LIKE ? ORDER BY updated_at DESC",
            (f"%{term}%", f"%{term}%"),
        )
        return await cur.fetchall()

    async def stats(self):
        cur = await self._db.execute("SELECT step, COUNT(*) c FROM users GROUP BY step")
        rows = await cur.fetchall()
        return {r["step"]: r["c"] for r in rows}

    async def stalled(self):
        """Users not yet completed/approved/rejected, for nudge checks.
        (await_uid IS included — they signed up but didn't send UID, worth chasing.)"""
        cur = await self._db.execute(
            "SELECT * FROM users WHERE step NOT IN (?,?,?)",
            (STEP_APPROVED, STEP_REJECTED, STEP_CLAIMED),
        )
        return await cur.fetchall()
