import logging
import sqlite3
from datetime import datetime

logger = logging.getLogger(__name__)

class ChatLogger:
    def __init__(self, db_path='chat_logs.db'):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize the database and create table if it doesn't exist."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS chat_messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        user_id TEXT NOT NULL,
                        username TEXT NOT NULL,
                        channel_id TEXT NOT NULL,
                        channel_name TEXT NOT NULL,
                        message_content TEXT NOT NULL
                    )
                ''')
                conn.commit()
        except sqlite3.Error as e:
            logger.error("Database initialization error", exc_info=True)
    
    def log_message(self, user_id, username, channel_id, channel_name, message_content):
        """Log a chat message to the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO chat_messages (timestamp, user_id, username, channel_id, channel_name, message_content)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (datetime.utcnow().isoformat(), str(user_id), username, str(channel_id), channel_name, message_content))
                conn.commit()
        except sqlite3.Error as e:
            logger.error("Failed to log message for user=%s channel=%s", username, channel_name, exc_info=True)
