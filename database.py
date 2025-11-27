import logging
import time
import secrets
from motor.motor_asyncio import AsyncIOMotorClient
from config import Config

logger = logging.getLogger(__name__)


class Database:
    def __init__(self):
        self.client = AsyncIOMotorClient(Config.MONGO_DB_URL)
        self.db = self.client[Config.DB_NAME]
        self.movies = self.db["movies"]
        self.users = self.db["users"]
        self.tokens = self.db["tokens"]
    
    # Movie operations
    async def add_movie(self, data: dict) -> bool:
        try:
            code = data["code"].lower().strip()
            data["code"] = code
            await self.movies.update_one(
                {"code": code},
                {"$set": data},
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Add movie error: {e}")
            return False
    
    async def get_movie(self, code: str) -> dict:
        if not code:
            return None
        return await self.movies.find_one({"code": code.lower().strip()})
    
    async def search_movies(self, query: str) -> list:
        if not query:
            return []
        
        # Search by code or title (case-insensitive)
        # Also search with underscores replaced by spaces
        search_query = query.replace("_", " ").replace(" ", "_")
        
        cursor = self.movies.find({
            "$or": [
                {"code": {"$regex": query.replace(" ", "_"), "$options": "i"}},
                {"title": {"$regex": query, "$options": "i"}},
                {"code": {"$regex": query, "$options": "i"}}
            ]
        }).limit(10)
        return await cursor.to_list(length=10)
    
    async def delete_movie(self, code: str) -> bool:
        result = await self.movies.delete_one({"code": code.lower().strip()})
        return result.deleted_count > 0
    
    async def get_all_movies(self) -> list:
        cursor = self.movies.find({})
        return await cursor.to_list(length=1000)
    
    # User operations
    async def add_user(self, user_id: int, username: str = None):
        await self.users.update_one(
            {"user_id": user_id},
            {"$set": {"user_id": user_id, "username": username}},
            upsert=True
        )
    
    async def get_user_count(self) -> int:
        return await self.users.count_documents({})
    
    async def get_all_users(self) -> list:
        cursor = self.users.find({})
        return await cursor.to_list(length=100000)
    
    # Token operations - Now includes quality
    async def create_token(self, user_id: int, movie_code: str, part: int = 1, quality: str = "") -> str:
        token = secrets.token_urlsafe(16)
        await self.tokens.insert_one({
            "token": token,
            "user_id": user_id,
            "movie_code": movie_code,
            "part": part,
            "quality": quality,
            "created_at": time.time(),
            "used": False
        })
        return token
    
    async def verify_token(self, token: str, user_id: int) -> dict:
        ten_min_ago = time.time() - 600
        return await self.tokens.find_one_and_update(
            {
                "token": token,
                "user_id": user_id,
                "used": False,
                "created_at": {"$gte": ten_min_ago}
            },
            {"$set": {"used": True}}
        )
    
    async def cleanup_tokens(self):
        one_hour_ago = time.time() - 3600
        await self.tokens.delete_many({"created_at": {"$lt": one_hour_ago}})


# Global instance
db = Database()