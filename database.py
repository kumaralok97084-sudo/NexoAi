from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import aiosqlite


class Database:
    def __init__(self, db_path: str = "nexoai.db") -> None:
        self.db_path = db_path

    async def init(self) -> None:
        Path(self.db_path).touch(exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS guild_settings (
                    guild_id INTEGER PRIMARY KEY,
                    ai_channel_id INTEGER,
                    auto_reply_enabled INTEGER DEFAULT 0,
                    support_channel_id INTEGER,
                    system_prompt TEXT
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id INTEGER PRIMARY KEY,
                    preferred_language TEXT DEFAULT 'en',
                    persona TEXT DEFAULT '',
                    agent_model TEXT DEFAULT ''
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS conversation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER,
                    channel_id INTEGER,
                    user_id INTEGER,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS file_ingestions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER,
                    channel_id INTEGER,
                    user_id INTEGER,
                    original_name TEXT NOT NULL,
                    stored_path TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS user_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    fact_key TEXT NOT NULL,
                    fact_value TEXT NOT NULL,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, fact_key)
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS user_warns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    warned_by INTEGER NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS moderation_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    reason TEXT,
                    details TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS conversation_summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    guild_id INTEGER,
                    channel_id INTEGER,
                    summary TEXT NOT NULL,
                    message_count INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS user_preferences (
                    user_id INTEGER PRIMARY KEY,
                    preferred_language TEXT DEFAULT '',
                    preferred_tone TEXT DEFAULT '',
                    communication_style TEXT DEFAULT '',
                    topics TEXT DEFAULT '[]',
                    learned_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS semantic_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    category TEXT NOT NULL,
                    content TEXT NOT NULL,
                    keywords TEXT DEFAULT '',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS message_tracking (
                    user_id INTEGER NOT NULL,
                    guild_id INTEGER DEFAULT 0,
                    channel_id INTEGER DEFAULT 0,
                    message_count INTEGER DEFAULT 1,
                    PRIMARY KEY (user_id, guild_id, channel_id)
                )
                """
            )
            for table_sql in [
                """CREATE TABLE IF NOT EXISTS tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL, channel_id INTEGER, status TEXT DEFAULT 'open',
                    subject TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)""",
                """CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
                    channel_id INTEGER, guild_id INTEGER, message TEXT,
                    remind_at DATETIME NOT NULL, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)""",
                """CREATE TABLE IF NOT EXISTS reaction_roles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL, message_id INTEGER NOT NULL,
                    role_id INTEGER NOT NULL, emoji TEXT NOT NULL)""",
                """CREATE TABLE IF NOT EXISTS custom_filters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER NOT NULL,
                    pattern TEXT NOT NULL, action TEXT DEFAULT 'warn',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP)""",
                """CREATE TABLE IF NOT EXISTS knowledge_base (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER DEFAULT 0,
                    user_id INTEGER DEFAULT 0, topic TEXT NOT NULL,
                    content TEXT NOT NULL, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)""",
                """CREATE TABLE IF NOT EXISTS chat_threads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
                    guild_id INTEGER, channel_id INTEGER, title TEXT,
                    active INTEGER DEFAULT 1, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)""",
                """CREATE TABLE IF NOT EXISTS server_logging (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER NOT NULL,
                    log_channel_id INTEGER, log_events TEXT DEFAULT 'all',
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP)""",
                """CREATE TABLE IF NOT EXISTS user_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
                    guild_id INTEGER, title TEXT, content TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP)""",
                """CREATE TABLE IF NOT EXISTS polls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER NOT NULL,
                    channel_id INTEGER, message_id INTEGER, question TEXT,
                    options TEXT, creator_id INTEGER, active INTEGER DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP)""",
            ]:
                await db.execute(table_sql)

            # Backward-compatible migration for older databases.
            for col in ("agent_model", "welcome_channel", "welcome_message", "leave_channel", "leave_message", "autorole_id",
                        "modlog_channel", "raid_mode", "antispam_enabled", "filter_mode"):
                try:
                    if col == "agent_model":
                        await db.execute("ALTER TABLE user_profiles ADD COLUMN agent_model TEXT DEFAULT ''")
                    else:
                        await db.execute(f"ALTER TABLE guild_settings ADD COLUMN {col} TEXT DEFAULT ''")
                except aiosqlite.OperationalError:
                    pass
            await db.commit()

    async def upsert_guild_setting(self, guild_id: int, key: str, value: Any) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO guild_settings (guild_id) VALUES (?)", (guild_id,)
            )
            await db.execute(
                f"UPDATE guild_settings SET {key} = ? WHERE guild_id = ?", (value, guild_id)
            )
            await db.commit()

    async def get_guild_setting(self, guild_id: int, key: str) -> Any:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                f"SELECT {key} FROM guild_settings WHERE guild_id = ?", (guild_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None

    async def add_message(
        self, guild_id: int, channel_id: int, user_id: int, role: str, content: str
    ) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO conversation_history (guild_id, channel_id, user_id, role, content)
                VALUES (?, ?, ?, ?, ?)
                """,
                (guild_id, channel_id, user_id, role, content[:3000]),
            )
            await db.commit()

    async def get_recent_messages(
        self, guild_id: int, channel_id: int, limit: int = 10
    ) -> list[dict[str, str]]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                """
                SELECT role, content
                FROM conversation_history
                WHERE guild_id = ? AND channel_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (guild_id, channel_id, limit),
            ) as cursor:
                rows = await cursor.fetchall()
        rows.reverse()
        return [{"role": role, "content": content} for role, content in rows]

    async def clear_channel_history(self, guild_id: int, channel_id: int) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM conversation_history WHERE guild_id = ? AND channel_id = ?",
                (guild_id, channel_id),
            )
            await db.commit()
            return cursor.rowcount

    async def add_file_record(
        self,
        guild_id: int,
        channel_id: int,
        user_id: int,
        original_name: str,
        stored_path: str,
    ) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO file_ingestions (guild_id, channel_id, user_id, original_name, stored_path)
                VALUES (?, ?, ?, ?, ?)
                """,
                (guild_id, channel_id, user_id, original_name, stored_path),
            )
            await db.commit()

    async def set_user_profile(self, user_id: int, key: str, value: str) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO user_profiles (user_id) VALUES (?)", (user_id,)
            )
            await db.execute(
                f"UPDATE user_profiles SET {key} = ? WHERE user_id = ?", (value, user_id)
            )
            await db.commit()

    async def get_user_profile(self, user_id: int) -> dict[str, str]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT preferred_language, persona, agent_model FROM user_profiles WHERE user_id = ?",
                (user_id,),
            ) as cursor:
                row = await cursor.fetchone()
        if not row:
            return {"preferred_language": "en", "persona": "", "agent_model": ""}
        return {"preferred_language": row[0], "persona": row[1], "agent_model": row[2]}

    async def set_user_memory(self, user_id: int, fact_key: str, fact_value: str) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO user_memory (user_id, fact_key, fact_value, updated_at)
                   VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                   ON CONFLICT(user_id, fact_key)
                   DO UPDATE SET fact_value = excluded.fact_value, updated_at = CURRENT_TIMESTAMP""",
                (user_id, fact_key, fact_value[:1000]),
            )
            await db.commit()

    async def get_user_memory(self, user_id: int) -> dict[str, str]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT fact_key, fact_value FROM user_memory WHERE user_id = ? ORDER BY updated_at DESC",
                (user_id,),
            ) as cursor:
                rows = await cursor.fetchall()
        return {key: val for key, val in rows}

    async def delete_user_memory(self, user_id: int, fact_key: str) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM user_memory WHERE user_id = ? AND fact_key = ?",
                (user_id, fact_key),
            )
            await db.commit()

    async def add_warn(self, guild_id: int, user_id: int, reason: str, warned_by: int) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "INSERT INTO user_warns (guild_id, user_id, reason, warned_by) VALUES (?, ?, ?, ?)",
                (guild_id, user_id, reason, warned_by),
            )
            await db.commit()
            return cursor.lastrowid or 0

    async def count_warns(self, guild_id: int, user_id: int) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT COUNT(*) FROM user_warns WHERE guild_id = ? AND user_id = ?",
                (guild_id, user_id),
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0

    async def get_warns(self, guild_id: int, user_id: int) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                """SELECT id, reason, warned_by, created_at
                   FROM user_warns
                   WHERE guild_id = ? AND user_id = ?
                   ORDER BY created_at DESC""",
                (guild_id, user_id),
            ) as cursor:
                rows = await cursor.fetchall()
        return [
            {"id": r[0], "reason": r[1], "warned_by": r[2], "created_at": r[3]}
            for r in rows
        ]

    async def delete_warn(self, warn_id: int) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM user_warns WHERE id = ?", (warn_id,))
            await db.commit()

    async def clear_warns(self, guild_id: int, user_id: int) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM user_warns WHERE guild_id = ? AND user_id = ?",
                (guild_id, user_id),
            )
            await db.commit()
            return cursor.rowcount

    async def add_moderation_log(
        self, guild_id: int, user_id: int, action: str, reason: str, details: str = ""
    ) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO moderation_logs (guild_id, user_id, action, reason, details) VALUES (?, ?, ?, ?, ?)",
                (guild_id, user_id, action, reason, details),
            )
            await db.commit()

    async def get_moderation_logs(
        self, guild_id: int, user_id: int, limit: int = 10
    ) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                """SELECT action, reason, details, created_at
                   FROM moderation_logs
                   WHERE guild_id = ? AND user_id = ?
                   ORDER BY created_at DESC LIMIT ?""",
                (guild_id, user_id, limit),
            ) as cursor:
                rows = await cursor.fetchall()
        return [
            {"action": r[0], "reason": r[1], "details": r[2], "created_at": r[3]}
            for r in rows
        ]

    async def get_recent_messages_by_user(
        self, user_id: int, guild_id: int, limit: int = 10
    ) -> list[dict[str, str]]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                """SELECT role, content FROM conversation_history
                   WHERE user_id = ? AND guild_id = ?
                   ORDER BY id DESC LIMIT ?""",
                (user_id, guild_id, limit),
            ) as cursor:
                rows = await cursor.fetchall()
        rows.reverse()
        return [{"role": role, "content": content} for role, content in rows]

    async def upsert_message_count(self, user_id: int, guild_id: int, channel_id: int) -> int:
        gid = guild_id or 0
        cid = channel_id or 0
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO message_tracking (user_id, guild_id, channel_id, message_count)
                   VALUES (?, ?, ?, 1)
                   ON CONFLICT(user_id, guild_id, channel_id)
                   DO UPDATE SET message_count = message_count + 1""",
                (user_id, gid, cid),
            )
            await db.commit()
            async with db.execute(
                "SELECT message_count FROM message_tracking WHERE user_id = ? AND guild_id = ? AND channel_id = ?",
                (user_id, gid, cid),
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0

    async def reset_message_count(self, user_id: int, guild_id: int, channel_id: int) -> None:
        gid = guild_id or 0
        cid = channel_id or 0
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM message_tracking WHERE user_id = ? AND guild_id = ? AND channel_id = ?",
                (user_id, gid, cid),
            )
            await db.commit()

    async def store_summary(self, user_id: int, guild_id: int, channel_id: int, summary: str, message_count: int) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO conversation_summaries (user_id, guild_id, channel_id, summary, message_count)
                   VALUES (?, ?, ?, ?, ?)""",
                (user_id, guild_id or 0, channel_id or 0, summary[:2000], message_count),
            )
            await db.commit()

    async def get_latest_summary(self, user_id: int, guild_id: int, channel_id: int) -> str | None:
        gid = guild_id or 0
        cid = channel_id or 0
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                """SELECT summary FROM conversation_summaries
                   WHERE user_id = ? AND guild_id = ? AND channel_id = ?
                   ORDER BY created_at DESC LIMIT 1""",
                (user_id, gid, cid),
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None

    async def set_user_preferences(self, user_id: int, language: str, tone: str, style: str, topics: list[str]) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO user_preferences (user_id, preferred_language, preferred_tone, communication_style, topics, learned_at)
                   VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                   ON CONFLICT(user_id)
                   DO UPDATE SET preferred_language = excluded.preferred_language,
                                 preferred_tone = excluded.preferred_tone,
                                 communication_style = excluded.communication_style,
                                 topics = excluded.topics,
                                 learned_at = CURRENT_TIMESTAMP""",
                (user_id, language[:50], tone[:50], style[:100], json.dumps(topics[:20])),
            )
            await db.commit()

    async def get_user_preferences(self, user_id: int) -> dict[str, str | list[str]]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT preferred_language, preferred_tone, communication_style, topics FROM user_preferences WHERE user_id = ?",
                (user_id,),
            ) as cursor:
                row = await cursor.fetchone()
        if not row:
            return {"preferred_language": "", "preferred_tone": "", "communication_style": "", "topics": []}
        topics = self.safe_json_load(row[3])
        return {
            "preferred_language": row[0] or "",
            "preferred_tone": row[1] or "",
            "communication_style": row[2] or "",
            "topics": topics if isinstance(topics, list) else [],
        }

    async def store_semantic_memory(self, user_id: int, category: str, content: str, keywords: str) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO semantic_memory (user_id, category, content, keywords)
                   VALUES (?, ?, ?, ?)""",
                (user_id, category[:50], content[:1000], keywords[:300]),
            )
            await db.commit()

    async def get_semantic_memories(self, user_id: int, limit: int = 20) -> list[dict[str, str]]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                """SELECT category, content, keywords FROM semantic_memory
                   WHERE user_id = ? ORDER BY created_at DESC LIMIT ?""",
                (user_id, limit),
            ) as cursor:
                rows = await cursor.fetchall()
        return [{"category": r[0], "content": r[1], "keywords": r[2]} for r in rows]

    async def search_semantic_memory(self, user_id: int, search_terms: list[str], limit: int = 5) -> list[dict[str, str]]:
        if not search_terms:
            return []
        async with aiosqlite.connect(self.db_path) as db:
            query = """SELECT category, content, keywords FROM semantic_memory
                       WHERE user_id = ? AND ("""
            conditions = []
            params: list[Any] = [user_id]
            for term in search_terms:
                conditions.append("(content LIKE ? OR keywords LIKE ?)")
                params.extend([f"%{term}%", f"%{term}%"])
            query += " OR ".join(conditions) + f") ORDER BY created_at DESC LIMIT {limit}"
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
        return [{"category": r[0], "content": r[1], "keywords": r[2]} for r in rows]

    async def clear_semantic_memory(self, user_id: int) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM semantic_memory WHERE user_id = ?", (user_id,))
            await db.commit()

    # --- Knowledge Base ---
    async def add_knowledge(self, guild_id: int, user_id: int, topic: str, content: str) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO knowledge_base (guild_id, user_id, topic, content) VALUES (?, ?, ?, ?)",
                (guild_id, user_id, topic[:200], content[:2000]),
            )
            await db.commit()

    async def search_knowledge(self, guild_id: int, query: str, limit: int = 5) -> list[dict[str, str]]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                """SELECT topic, content FROM knowledge_base
                   WHERE guild_id = ? AND (topic LIKE ? OR content LIKE ?)
                   ORDER BY created_at DESC LIMIT ?""",
                (guild_id, f"%{query}%", f"%{query}%", limit),
            ) as cursor:
                rows = await cursor.fetchall()
        return [{"topic": r[0], "content": r[1]} for r in rows]

    async def list_knowledge(self, guild_id: int) -> list[dict[str, str]]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT id, topic, content FROM knowledge_base WHERE guild_id = ? ORDER BY created_at DESC LIMIT 50",
                (guild_id,),
            ) as cursor:
                rows = await cursor.fetchall()
        return [{"id": str(r[0]), "topic": r[1], "content": r[2][:100]} for r in rows]

    async def delete_knowledge(self, knowledge_id: int) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM knowledge_base WHERE id = ?", (knowledge_id,))
            await db.commit()

    # --- Chat Threads ---
    async def create_thread(self, user_id: int, guild_id: int, channel_id: int, title: str) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "INSERT INTO chat_threads (user_id, guild_id, channel_id, title) VALUES (?, ?, ?, ?)",
                (user_id, guild_id, channel_id, title[:100]),
            )
            await db.commit()
            return cursor.lastrowid or 0

    async def get_active_thread(self, user_id: int, guild_id: int, channel_id: int) -> dict | None:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                """SELECT id, title FROM chat_threads
                   WHERE user_id = ? AND guild_id = ? AND channel_id = ? AND active = 1
                   ORDER BY created_at DESC LIMIT 1""",
                (user_id, guild_id, channel_id),
            ) as cursor:
                row = await cursor.fetchone()
        return {"id": row[0], "title": row[1]} if row else None

    async def close_thread(self, thread_id: int) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE chat_threads SET active = 0 WHERE id = ?", (thread_id,))
            await db.commit()

    # --- Custom Filters ---
    async def add_filter(self, guild_id: int, pattern: str, action: str = "warn") -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO custom_filters (guild_id, pattern, action) VALUES (?, ?, ?)",
                (guild_id, pattern[:200], action),
            )
            await db.commit()

    async def remove_filter(self, filter_id: int) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM custom_filters WHERE id = ?", (filter_id,))
            await db.commit()

    async def get_filters(self, guild_id: int) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT id, pattern, action FROM custom_filters WHERE guild_id = ?", (guild_id,),
            ) as cursor:
                rows = await cursor.fetchall()
        return [{"id": r[0], "pattern": r[1], "action": r[2]} for r in rows]

    # --- Reminders ---
    async def add_reminder(self, user_id: int, channel_id: int, guild_id: int, message: str, remind_at: str) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "INSERT INTO reminders (user_id, channel_id, guild_id, message, remind_at) VALUES (?, ?, ?, ?, ?)",
                (user_id, channel_id, guild_id, message[:500], remind_at),
            )
            await db.commit()
            return cursor.lastrowid or 0

    async def get_due_reminders(self) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT id, user_id, channel_id, guild_id, message FROM reminders WHERE remind_at <= datetime('now')",
            ) as cursor:
                rows = await cursor.fetchall()
        return [{"id": r[0], "user_id": r[1], "channel_id": r[2], "guild_id": r[3], "message": r[4]} for r in rows]

    async def delete_reminder(self, reminder_id: int) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
            await db.commit()

    # --- Notes ---
    async def add_note(self, user_id: int, guild_id: int, title: str, content: str) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "INSERT INTO user_notes (user_id, guild_id, title, content) VALUES (?, ?, ?, ?)",
                (user_id, guild_id, title[:200], content[:2000]),
            )
            await db.commit()
            return cursor.lastrowid or 0

    async def get_notes(self, user_id: int, guild_id: int) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT id, title, content FROM user_notes WHERE user_id = ? AND guild_id = ? ORDER BY created_at DESC LIMIT 20",
                (user_id, guild_id),
            ) as cursor:
                rows = await cursor.fetchall()
        return [{"id": r[0], "title": r[1], "content": r[2]} for r in rows]

    async def delete_note(self, note_id: int) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM user_notes WHERE id = ?", (note_id,))
            await db.commit()

    # --- Polls ---
    async def create_poll(self, guild_id: int, channel_id: int, message_id: int, question: str, options: str, creator_id: int) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "INSERT INTO polls (guild_id, channel_id, message_id, question, options, creator_id) VALUES (?, ?, ?, ?, ?, ?)",
                (guild_id, channel_id, message_id, question[:300], options[:1000], creator_id),
            )
            await db.commit()
            return cursor.lastrowid or 0

    async def close_poll(self, poll_id: int) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE polls SET active = 0 WHERE id = ?", (poll_id,))
            await db.commit()

    # --- Reaction Roles ---
    async def add_reaction_role(self, guild_id: int, channel_id: int, message_id: int, role_id: int, emoji: str) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO reaction_roles (guild_id, channel_id, message_id, role_id, emoji) VALUES (?, ?, ?, ?, ?)",
                (guild_id, channel_id, message_id, role_id, emoji),
            )
            await db.commit()

    async def get_reaction_roles(self, guild_id: int, channel_id: int, message_id: int) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT role_id, emoji FROM reaction_roles WHERE guild_id = ? AND channel_id = ? AND message_id = ?",
                (guild_id, channel_id, message_id),
            ) as cursor:
                rows = await cursor.fetchall()
        return [{"role_id": str(r[0]), "emoji": r[1]} for r in rows]

    # --- Maintenance ---
    async def cleanup_old_data(self, days: int = 30) -> dict[str, int]:
        counts: dict[str, int] = {}
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                f"DELETE FROM moderation_logs WHERE created_at < datetime('now', '-{days} days')"
            )
            counts["moderation_logs"] = cursor.rowcount
            cursor = await db.execute(
                "DELETE FROM reminders WHERE remind_at < datetime('now', '-7 days')"
            )
            counts["reminders"] = cursor.rowcount
            await db.commit()
        return counts

    @staticmethod
    def safe_json_load(raw: str | None) -> dict[str, Any] | list[Any]:
        if not raw:
            return {} if raw is None else []
        try:
            value = json.loads(raw)
            return value if isinstance(value, (dict, list)) else ({} if isinstance(value, str) else value)
        except json.JSONDecodeError:
            return {} if raw is None else []
