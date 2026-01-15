import os
from typing import Optional

class Config:
    def __init__(self):
        self._load_config()
    
    def _load_config(self):
        try:
            if not os.path.exists('.env'):
                raise FileNotFoundError("Configuration file '.env' not found")
            
            # Load .env file manually
            with open('.env', 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip()
            
            # Validate required keys
            required_keys = ['discordKey', 'session', 'GROQ_API_KEY', 'perplexity_api_key']
            for key in required_keys:
                if key not in os.environ:
                    raise KeyError(f"Required configuration key '{key}' not found in .env file")
                    
        except (FileNotFoundError, KeyError) as e:
            print(f"Configuration error: {e}")
            raise
    
    @property
    def discord_key(self) -> str:
        return os.environ['discordKey']
    
    @property
    def session_aod(self) -> str:
        return os.environ['session']
    
    @property
    def groq_key(self) -> str:
        return os.environ['GROQ_API_KEY']
    
    @property
    def perplexity_api_key(self) -> str:
        return os.environ['perplexity_api_key']

# Constants
COUNTS_FILE = "counts.json"
TASKS_FILE = "user_tasks.txt"
COMPLETIONS_FILE = "task_completions.json"
WELCOME_CHANNEL_ID = 611027490848374822
AUTHORIZED_USERS = ["fishermanguybro", "het_tanis"]
BOT_USERNAME = "fishermanguybot"
DISCORD_MESSAGE_CHUNK_SIZE = 1900  # Discord message limit with buffer
SIMPLE_COMMANDS = ["!roll", "!user_count", "!server_age", "!coinflip", "!labs", 
                   "!book", "!commands", "!joke", "!bot_stats"]

# API URLs
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
PERPLEXITY_URL = "https://api.perplexity.ai/chat/completions"
JOKE_API_URL = "https://icanhazdadjoke.com/"
EIGHTBALL_API_URL = "https://eightballapi.com/api"

# Channel names to exclude from weekly report topic detection
EXCLUDED_CHANNELS_FROM_TOPIC = {'sandbox', 'moderator-only', 'course-discussion-posts'}