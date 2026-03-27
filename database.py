"""
database.py — Persistência SQLite para Dragon's Breath / Ressoar
Gerencia saves de personagem. Autenticação via Clerk (clerk_user_id = TEXT).
"""
import json
import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.environ.get("DB_PATH", "ressoar.db")


def init_db() -> None:
    """Cria as tabelas se ainda não existirem."""
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS saves (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                clerk_user_id   TEXT    NOT NULL,
                character_name  TEXT    NOT NULL,
                character_class TEXT    NOT NULL DEFAULT 'Aventureiro',
                campaign_id     TEXT    NOT NULL,
                world_state     TEXT    NOT NULL,
                updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_saves_user ON saves(clerk_user_id);
        """)


@contextmanager
def get_db():
    """Context manager que entrega uma conexão SQLite com commit/rollback automático."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ─── Saves ────────────────────────────────────────────────────────────────────

def list_saves(clerk_user_id: str) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            """SELECT id, character_name, character_class, campaign_id,
                      updated_at
               FROM saves WHERE clerk_user_id = ?
               ORDER BY updated_at DESC""",
            (clerk_user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_save(save_id: int, clerk_user_id: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM saves WHERE id = ? AND clerk_user_id = ?",
            (save_id, clerk_user_id),
        ).fetchone()
        return dict(row) if row else None


def upsert_save(clerk_user_id: str, character_name: str, character_class: str,
                campaign_id: str, world_state: dict) -> int:
    """
    Salva (ou atualiza) o personagem.
    Um slot por (clerk_user_id, campaign_id, character_name).
    """
    ws_json = json.dumps(world_state, ensure_ascii=False)
    with get_db() as conn:
        existing = conn.execute(
            """SELECT id FROM saves
               WHERE clerk_user_id = ? AND campaign_id = ? AND character_name = ?""",
            (clerk_user_id, campaign_id, character_name),
        ).fetchone()

        if existing:
            conn.execute(
                """UPDATE saves
                   SET world_state = ?, character_class = ?,
                       updated_at = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                (ws_json, character_class, existing["id"]),
            )
            return existing["id"]
        else:
            cur = conn.execute(
                """INSERT INTO saves
                   (clerk_user_id, character_name, character_class, campaign_id, world_state)
                   VALUES (?, ?, ?, ?, ?)""",
                (clerk_user_id, character_name, character_class, campaign_id, ws_json),
            )
            return cur.lastrowid


def delete_save(save_id: int, clerk_user_id: str) -> bool:
    with get_db() as conn:
        cur = conn.execute(
            "DELETE FROM saves WHERE id = ? AND clerk_user_id = ?",
            (save_id, clerk_user_id),
        )
        return cur.rowcount > 0
