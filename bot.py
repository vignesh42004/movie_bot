#!/usr/bin/env python3
"""
Movie Bot - Main Entry Point with Flask for Render
Run: python bot.py
"""
import asyncio
import logging
import sys
import threading
import os
from flask import Flask, jsonify

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

# Flask app for Render port binding
app = Flask(__name__)

# Global bot instance
bot_instance = None
bot_username = None

@app.route('/')
def home():
    """Home route for health check"""
    return f"""
    <h1>🎬 Movie Bot Status</h1>
    <p>✅ Bot is running!</p>
    <p>👤 Bot: @{bot_username if bot_username else 'Starting...'}</p>
    <p>🔥 Server: Active</p>
    """, 200

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "bot": bot_username if bot_username else "starting",
        "service": "movie_bot"
    }), 200

@app.route('/status')
def status():
    """Detailed status endpoint"""
    return jsonify({
        "running": bot_instance is not None,
        "bot_username": bot_username,
        "version": "1.0.0"
    }), 200


async def run_bot():
    """Run the Pyrogram bot"""
    global bot_instance, bot_username
    
    # Validate config
    try:
        Config.validate()
        logger.info("✅ Config OK")
    except ValueError as e:
        logger.error(f"❌ Config Error: {e}")
        sys.exit(1)
    
    # Create bot
    bot_instance = Client(
        name="movie_bot",
        api_id=Config.API_ID,
        api_hash=Config.API_HASH,
        bot_token=Config.BOT_TOKEN
    )
    
    # Register handlers
    register_all_handlers(bot_instance)
    logger.info("✅ Handlers registered")
    
    # Start
    try:
        await bot_instance.start()
        me = await bot_instance.get_me()
        bot_username = me.username
        logger.info(f"✅ Bot started: @{bot_username}")
        
        # Keep running
        await asyncio.Event().wait()
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
    finally:
        await bot_instance.stop()


def start_bot_thread():
    """Start bot in a separate thread with its own event loop"""
    # Create new event loop for this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Run bot
    loop.run_until_complete(run_bot())


if __name__ == "__main__":
    print("""
╔════════════════════════════════╗
║     🎬 MOVIE BOT STARTING      ║
╚════════════════════════════════╝
    """)
    
    # Start bot in background thread
    bot_thread = threading.Thread(target=start_bot_thread, daemon=True)
    bot_thread.start()
    logger.info("✅ Bot thread started")
    
    # Get port from environment (Render provides this)
    port = int(os.environ.get("PORT", 10000))
    
    # Run Flask (this keeps the main thread busy and port open)
    logger.info(f"🌐 Starting web server on port {port}")
    
    # Disable Flask debug messages
    import logging as flask_logging
    flask_logging.getLogger('werkzeug').setLevel(flask_logging.WARNING)
    
    # Run Flask app
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False,
        use_reloader=False  # Important: prevent double bot start
    )
