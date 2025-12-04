import logging
import aiohttp
import base64
import re
from config import Config

logger = logging.getLogger(__name__)


async def get_movie_info(query: str) -> dict:
    """Get movie info from TMDB"""
    if not Config.TMDB_API_KEY or not query:
        return None
    
    try:
        url = "https://api.themoviedb.org/3/search/movie"
        params = {"api_key": Config.TMDB_API_KEY, "query": query}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("results"):
                        m = data["results"][0]
                        poster = f"https://image.tmdb.org/t/p/w500{m['poster_path']}" if m.get("poster_path") else None
                        overview = m.get("overview", "")[:300]
                        return {
                            "title": m.get("title", "Unknown"),
                            "year": m.get("release_date", "")[:4],
                            "rating": m.get("vote_average", "N/A"),
                            "overview": overview,
                            "poster": poster
                        }
        return None
    except Exception as e:
        logger.error(f"TMDB error: {e}")
        return None


async def check_subscription(bot, user_id: int) -> bool:
    """Check if user joined channel"""
    if not Config.BACKUP_CHANNEL_ID:
        return True
    
    try:
        member = await bot.get_chat_member(Config.BACKUP_CHANNEL_ID, user_id)
        status = str(member.status).lower()
        return any(s in status for s in ["member", "administrator", "creator", "owner"])
    except Exception as e:
        error = str(e).lower()
        if "user_not_participant" in error:
            return False
        if "chat_admin_required" in error:
            logger.warning("Bot is not admin in channel!")
            return True
        return True


def encode_payload(movie_code: str, part: int = 1, quality: str = "", token: str = "") -> str:
    """Encode data to base64"""
    try:
        data = f"{movie_code}|{part}|{quality}|{token}"
        return base64.urlsafe_b64encode(data.encode()).decode()
    except:
        return ""


def decode_payload(payload: str) -> tuple:
    """Decode base64 to data"""
    try:
        if not payload:
            return "", 1, "", ""
        
        decoded = base64.urlsafe_b64decode(payload.encode()).decode()
        
        if "|" not in decoded:
            return "", 1, "", ""
        
        parts = decoded.split("|")
        movie_code = parts[0].strip() if parts else ""
        part = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1
        quality = parts[2].strip() if len(parts) > 2 else ""
        token = parts[3].strip() if len(parts) > 3 else ""
        
        return movie_code, part, quality, token
    except:
        return "", 1, "", ""


def normalize_name(text: str) -> str:
    """Normalize movie name"""
    text = re.sub(r'[^\w\s]', '', text)
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)
    return text
