#!/usr/bin/env python3
"""
Movie Bot - Main Entry Point
Run: python bot.py
"""
import telebot
import asyncio
import logging
import sys


# Event loop fix
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

from pyrogram import Client
from pyrogram.enums import ParseMode
from config import Config
from handlers import register_all_handlers
from database import db

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
logging.getLogger("pyrogram").setLevel(logging.WARNING)


async def main():
    # Validate config
    try:
        Config.validate()
        logger.info("✅ Config OK")
    except ValueError as e:
        logger.error(f"❌ Config Error: {e}")
        sys.exit(1)
    
    # Create bot
    app = Client(
        name="movie_bot",
        api_id=Config.API_ID,
        api_hash=Config.API_HASH,
        bot_token=Config.BOT_TOKEN
    )
    
    # Register handlers
    register_all_handlers(app)
    logger.info("✅ Handlers registered")
    
    # Start
    try:
        await app.start()
        me = await app.get_me()
        logger.info(f"✅ Bot started: @{me.username}")
        
        # Keep running
        await asyncio.Event().wait()
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
    finally:
        await app.stop()


if __name__ == "__main__":
    print("""
╔════════════════════════════════╗
║     🎬 MOVIE BOT STARTING      ║
╚════════════════════════════════╝
    """)
    asyncio.run(main())
    