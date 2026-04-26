import fcntl
import json
import logging
import os
from datetime import datetime
from typing import Dict, Optional
from config import COUNTS_FILE

logger = logging.getLogger(__name__)

def increment_count(count_type: str) -> None:
    """Increment and track counts for bot statistics."""
    try:
        # Open or create the file, then lock for atomic read-modify-write
        fd = os.open(COUNTS_FILE, os.O_RDWR | os.O_CREAT)
        with os.fdopen(fd, "r+") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            content = f.read()
            counts = json.loads(content) if content else {}

            if count_type not in counts:
                counts[count_type] = {"all_time": 0, "weekly": {}}

            counts[count_type]["all_time"] += 1

            now = datetime.now()
            current_week = now.isocalendar()[1]
            current_year = now.year
            week_key = f"{current_year}-{current_week}"

            if week_key not in counts[count_type]["weekly"]:
                counts[count_type]["weekly"][week_key] = 0
            counts[count_type]["weekly"][week_key] += 1

            f.seek(0)
            f.truncate()
            json.dump(counts, f)
    except (IOError, json.JSONDecodeError) as e:
        logger.warning("Error updating counts file: %s", e)

def get_bot_stats() -> Optional[Dict]:
    """Get bot statistics from counts file."""
    try:
        with open(COUNTS_FILE, "r") as f:
            counts = json.load(f)
        
        now = datetime.now()
        current_week = now.isocalendar()[1]
        current_year = now.year
        week_key = f"{current_year}-{current_week}"
        
        return {
            "welcome_all_time": counts.get("welcome", {}).get("all_time", 0),
            "ask_all_time": counts.get("ask", {}).get("all_time", 0),
            "welcome_weekly": counts.get("welcome", {}).get("weekly", {}).get(week_key, 0),
            "ask_weekly": counts.get("ask", {}).get("weekly", {}).get(week_key, 0),
            "current_week": current_week
        }
    except FileNotFoundError:
        logger.debug("Counts file not found for get_bot_stats")
        return None

def parse_command_args(message: str, command: str) -> Optional[str]:
    """Safely parse command arguments from message."""
    # Use case-insensitive comparison for command, but preserve args case
    if not message.lower().startswith(f"{command.lower()} "):
        return None
    # Extract args from original message to preserve case
    args = message[len(command):].strip()
    return args if args else None