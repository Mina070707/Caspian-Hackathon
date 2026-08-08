import sqlite3
from datetime import datetime, timedelta, timezone
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "relay.db")

def get_connection():
    """Connects to the local SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Returns dict-like rows for clean field access
    return conn

def init_db():
    """Initializes the database schema if tables do not exist."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Table 1: Ephemeral pairing codes generated on Discord
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pending_codes (
                code TEXT PRIMARY KEY,
                discord_channel_id TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL
            );
        """)
        
        # Table 2: Active Gmail <-> Discord routes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS relay_pairings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                discord_channel_id TEXT NOT NULL,
                gmail_address TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                UNIQUE(discord_channel_id, gmail_address)
            );
        """)
        conn.commit()

# --- Pending Codes Functions ---

def save_pending_code(code: str, discord_channel_id: str):
    """Saves a newly generated Discord pin code."""
    now = datetime.now(timezone.utc)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO pending_codes (code, discord_channel_id, created_at) VALUES (?, ?, ?)",
            (code.upper(), discord_channel_id, now)
        )
        conn.commit()

def verify_and_consume_code(code: str, expiration_minutes: int = 15):
    """
    Checks if a code exists and is valid (not expired).
    If valid, deletes it and returns the associated discord_channel_id.
    """
    code_clean = code.strip().upper()
    now = datetime.now(timezone.utc)
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT discord_channel_id, created_at FROM pending_codes WHERE code = ?", (code_clean,))
        row = cursor.fetchone()
        
        if not row:
            return None  # Invalid code
        
        created_at = datetime.fromisoformat(row["created_at"])
        if now - created_at > timedelta(minutes=expiration_minutes):
            # Code expired -> purge it
            cursor.execute("DELETE FROM pending_codes WHERE code = ?", (code_clean,))
            conn.commit()
            return None
        
        # Code valid -> consume it (delete so it can't be reused)
        discord_channel_id = row["discord_channel_id"]
        cursor.execute("DELETE FROM pending_codes WHERE code = ?", (code_clean,))
        conn.commit()
        return discord_channel_id

# --- Relay Pairings Functions ---

def add_pairing(discord_channel_id: str, gmail_address: str):
    """Establishes an active route between a Gmail address and a Discord Channel."""
    now = datetime.now(timezone.utc)
    email_clean = gmail_address.strip().lower()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO relay_pairings (discord_channel_id, gmail_address, created_at) VALUES (?, ?, ?)",
            (discord_channel_id, email_clean, now)
        )
        conn.commit()

def get_channel_id_for_gmail(gmail_address: str) -> list[str]:
    """Finds all Discord Channels paired with a specific Gmail address."""
    email_clean = gmail_address.strip().lower()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT discord_channel_id FROM relay_pairings WHERE gmail_address = ?", (email_clean,))
        rows = cursor.fetchall()
        return [row["discord_channel_id"] for row in rows]

def get_gmails_for_channel(discord_channel_id: str) -> list[str]:
    """Finds all Gmail addresses listening on a specific Discord Channel."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT gmail_address FROM relay_pairings WHERE discord_channel_id = ?", (discord_channel_id,))
        rows = cursor.fetchall()
        return [row["gmail_address"] for row in rows]

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully!")