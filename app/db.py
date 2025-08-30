import sqlite3
import os
from typing import Any, Dict, Optional, Tuple
from flask import current_app, g


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        db_path = current_app.config["DATABASE_PATH"]
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        conn.row_factory = sqlite3.Row
        g.db = conn
    return g.db  # type: ignore


def close_db(_e: Optional[BaseException] = None) -> None:
    db: Optional[sqlite3.Connection] = g.pop("db", None)  # type: ignore
    if db is not None:
        db.close()


def init_db(app) -> None:
    with app.app_context():
        db = get_db()
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS captures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_path TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS detections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                capture_id INTEGER NOT NULL,
                disease TEXT,
                severity REAL,
                raw_json TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(capture_id) REFERENCES captures(id)
            );

            CREATE TABLE IF NOT EXISTS actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                detection_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                duration_ms INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(detection_id) REFERENCES detections(id)
            );
            """
        )
        db.commit()

    app.teardown_appcontext(close_db)


def insert_capture(image_path: str) -> int:
    db = get_db()
    cur = db.execute("INSERT INTO captures (image_path) VALUES (?)", (image_path,))
    db.commit()
    return int(cur.lastrowid)


def insert_detection(capture_id: int, disease: str, severity: float, raw_json: str) -> int:
    db = get_db()
    cur = db.execute(
        "INSERT INTO detections (capture_id, disease, severity, raw_json) VALUES (?, ?, ?, ?)",
        (capture_id, disease, severity, raw_json),
    )
    db.commit()
    return int(cur.lastrowid)


def insert_action(detection_id: int, action: str, duration_ms: int) -> int:
    db = get_db()
    cur = db.execute(
        "INSERT INTO actions (detection_id, action, duration_ms) VALUES (?, ?, ?)",
        (detection_id, action, duration_ms),
    )
    db.commit()
    return int(cur.lastrowid)


def get_recent(limit: int = 20) -> Tuple[list, list, list]:
    db = get_db()
    captures = db.execute("SELECT * FROM captures ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    detections = db.execute(
        "SELECT d.*, c.image_path FROM detections d JOIN captures c ON d.capture_id = c.id ORDER BY d.id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    actions = db.execute(
        "SELECT a.*, d.disease, d.severity FROM actions a JOIN detections d ON a.detection_id = d.id ORDER BY a.id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return list(captures), list(detections), list(actions) 