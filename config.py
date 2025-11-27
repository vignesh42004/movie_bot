import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Telegram
    API_ID = int(os.environ.get("API_ID", 0))
    API_HASH = os.environ.get("API_HASH", "")
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
    
    # Admin
    ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))
    
    # Channel
    BACKUP_CHANNEL_ID = int(os.environ.get("BACKUP_CHANNEL_ID", 0))
    BACKUP_CHANNEL_LINK = os.environ.get("BACKUP_CHANNEL_LINK", "")
    
    # Database
    MONGO_DB_URL = os.environ.get("MONGO_DB_URL", "")
    DB_NAME = os.environ.get("DB_NAME", "MovieBot")
    
    # GP Links
    GPLINKS_API_KEY = os.environ.get("GPLINKS_API_KEY", "")
    GPLINKS_API_URL = "https://gplinks.com/api"
    
    # TMDB
    TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "")
    
    @classmethod
    def validate(cls):
        required = [
            ("API_ID", cls.API_ID),
            ("API_HASH", cls.API_HASH),
            ("BOT_TOKEN", cls.BOT_TOKEN),
            ("ADMIN_ID", cls.ADMIN_ID),
            ("MONGO_DB_URL", cls.MONGO_DB_URL),
        ]
        missing = [name for name, value in required if not value]
        if missing:
            raise ValueError(f"Missing: {', '.join(missing)}")
        return True