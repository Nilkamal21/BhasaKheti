import sqlite3
import os
from pathlib import Path
from app.core.config import settings
from app.core.logging import logger


def get_db_path() -> Path:
    # Extract path from sqlite:///./bhasakheti.db
    raw_path = settings.DATABASE_URL.replace("sqlite:///", "")
    return Path(raw_path).resolve()


def init_db():
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info(f"Initializing SQLite database at {db_path}")

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        # Create minimal app_meta table to track schema versions and initialization status
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS app_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute(
            """
            INSERT OR IGNORE INTO app_meta (key, value)
            VALUES ('schema_version', '1.0.0')
            """
        )
        cursor.execute(
            """
            INSERT OR IGNORE INTO app_meta (key, value)
            VALUES ('initialization_phase', 'phase_5')
            """
        )
        
        # Create agricultural_knowledge table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS agricultural_knowledge (
                id TEXT PRIMARY KEY,
                title_bn TEXT NOT NULL,
                title_en TEXT NOT NULL,
                crop TEXT NOT NULL,
                category TEXT NOT NULL,
                topic TEXT NOT NULL,
                growth_stage TEXT,
                content_bn TEXT NOT NULL,
                content_en TEXT NOT NULL,
                source_org TEXT NOT NULL,
                source_url TEXT NOT NULL,
                publication_date TEXT NOT NULL,
                last_verified_date TEXT NOT NULL,
                geographic_scope TEXT NOT NULL,
                evidence_status TEXT NOT NULL,
                safety_notes_bn TEXT NOT NULL,
                safety_notes_en TEXT NOT NULL,
                keywords TEXT NOT NULL,
                chemical_control_permitted INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        
        # Sync verified knowledge records from json file if available
        import json
        kb_path = Path(settings.KNOWLEDGE_BASE_PATH).resolve()
        if kb_path.exists():
            try:
                with open(kb_path, "r", encoding="utf-8") as f:
                    records = json.load(f)
                for r in records:
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO agricultural_knowledge (
                            id, title_bn, title_en, crop, category, topic, growth_stage,
                            content_bn, content_en, source_org, source_url, publication_date,
                            last_verified_date, geographic_scope, evidence_status,
                            safety_notes_bn, safety_notes_en, keywords, chemical_control_permitted
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            r["id"], r["title_bn"], r["title_en"], r["crop"], r["category"],
                            r["topic"], r.get("growth_stage"), r["content_bn"], r["content_en"],
                            r["source_org"], r["source_url"], r["publication_date"],
                            r["last_verified_date"], r["geographic_scope"], r["evidence_status"],
                            r["safety_notes_bn"], r["safety_notes_en"],
                            json.dumps(r.get("keywords", []), ensure_ascii=False),
                            1 if r.get("chemical_control_permitted") else 0
                        )
                    )
                logger.info(f"Loaded {len(records)} verified agricultural knowledge records into database.")
            except Exception as e:
                logger.error(f"Error seeding agricultural knowledge database: {e}")

        conn.commit()
    logger.info("Database initialized successfully.")


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def check_db_health() -> bool:
    try:
        db_path = get_db_path()
        if not db_path.exists():
            return False
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            return cursor.fetchone() == (1,)
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False
