import sqlite3
from pathlib import Path

from flask import current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS organizations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    short_name TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('org', 'admin')),
    name TEXT NOT NULL,
    borrower_type TEXT NOT NULL DEFAULT 'mahasiswa',
    organization_id INTEGER REFERENCES organizations(id),
    phone TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rooms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    building TEXT NOT NULL,
    floor TEXT,
    kind TEXT NOT NULL,
    description TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reservations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    room_id INTEGER REFERENCES rooms(id),
    custom_room TEXT,
    borrower_type TEXT NOT NULL DEFAULT 'mahasiswa',
    identity_number TEXT,
    date TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    purpose TEXT NOT NULL,
    pic_name TEXT NOT NULL,
    pic_phone TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'approved', 'rejected', 'cancelled')),
    admin_id INTEGER REFERENCES users(id),
    note TEXT,
    created_at TEXT NOT NULL,
    decided_at TEXT,
    cancelled_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_reservations_slot
    ON reservations (room_id, date, start_time, end_time, status);

CREATE TABLE IF NOT EXISTS reservation_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reservation_id INTEGER NOT NULL REFERENCES reservations(id) ON DELETE CASCADE,
    actor_id INTEGER REFERENCES users(id),
    actor_role TEXT NOT NULL,
    action TEXT NOT NULL,
    note TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    reservation_id INTEGER REFERENCES reservations(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    read_at TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
        g.db.isolation_level = None
    return g.db


def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    from seed import seed_database

    db = get_db()
    db.executescript(SCHEMA)
    columns = [row[1] for row in db.execute("PRAGMA table_info(users)").fetchall()]
    if "email" not in columns:
        db.execute("ALTER TABLE users ADD COLUMN email TEXT")
    if "borrower_type" not in columns:
        db.execute("ALTER TABLE users ADD COLUMN borrower_type TEXT DEFAULT 'mahasiswa'")
    db.execute(
        """UPDATE users SET email = lower(username) || '@idbbali.ac.id'
           WHERE email IS NULL AND role = 'org'"""
    )
    db.execute(
        "UPDATE users SET email = 'admin@idbbali.ac.id' WHERE email IS NULL AND role = 'admin'"
    )
    db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users (email)")

    reservation_columns = [
        row[1] for row in db.execute("PRAGMA table_info(reservations)").fetchall()
    ]
    if "borrower_type" not in reservation_columns:
        db.execute("ALTER TABLE reservations ADD COLUMN borrower_type TEXT DEFAULT 'mahasiswa'")
    if "identity_number" not in reservation_columns:
        db.execute("ALTER TABLE reservations ADD COLUMN identity_number TEXT")
    db.execute(
        """UPDATE reservations
           SET borrower_type = CASE
               WHEN organization_id IN (SELECT id FROM organizations WHERE name LIKE '%BEM%')
               THEN 'organisasi' ELSE 'mahasiswa' END
           WHERE borrower_type IS NULL"""
    )
    db.execute(
        "UPDATE reservations SET borrower_type = 'mahasiswa' WHERE borrower_type IN ('organisasi', 'bem')"
    )
    db.execute(
        "UPDATE users SET borrower_type = 'mahasiswa' WHERE borrower_type = 'organisasi'"
    )
    seed_database(db)


def ensure_database(app):
    Path(app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)
    with app.app_context():
        init_db()


def register_cli(app):
    @app.cli.command("init-db")
    def init_db_command():
        init_db()
        print("Database siap.")

    @app.cli.command("reset-db")
    def reset_db_command():
        db = get_db()
        for table in (
            "notifications",
            "reservation_events",
            "reservations",
            "users",
            "rooms",
            "organizations",
            "settings",
        ):
            db.execute(f"DELETE FROM {table}")
        db.execute("DELETE FROM sqlite_sequence")
        init_db()
        print("Database direset dan diisi data awal.")
