if __name__ == "__main__":
    exit("Run bot.py instead!")

import logging
import asyncio
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait
from config import Config
from database import db
from helpers import (
    check_subscription,
    get_movie_info,
    encode_payload,
    decode_payload,
    normalize_name
)
from utils.monetize import create_download_link, is_monetization_enabled

logger = logging.getLogger(__name__)


# ============ SAFE REPLY HELPER ============
async def safe_reply(message: Message, text: str, **kwargs):
    """Send reply with FloodWait handling"""
    try:
        return await message.reply_text(text, **kwargs)
    except FloodWait as e:
        logger.warning(f"FloodWait: sleeping {e.value} seconds")
        await asyncio.sleep(e.value)
        return await message.reply_text(text, **kwargs)
    except Exception as e:
        logger.error(f"Reply error: {e}")
        return None


async def safe_edit(message: Message, text: str, **kwargs):
    """Edit message with FloodWait handling"""
    try:
        return await message.edit_text(text, **kwargs)
    except FloodWait as e:
        logger.warning(f"FloodWait: sleeping {e.value} seconds")
        await asyncio.sleep(e.value)
        return await message.edit_text(text, **kwargs)
    except Exception as e:
        logger.error(f"Edit error: {e}")
        return None


def register_user_handlers(app: Client):
    
    # ============ /start COMMAND ============
    @app.on_message(filters.command("start") & filters.private)
    async def start_cmd(bot: Client, message: Message):
        user_id = message.from_user.id
        username = message.from_user.username
        text = message.text.strip()
        
        logger.info(f"START from {user_id}: {text}")
        
        await db.add_user(user_id, username)
        
        parts = text.split(maxsplit=1)
        
        if len(parts) == 1:
            await send_welcome(message)
            return
        
        payload = parts[1].strip()
        
        if not payload:
            await send_welcome(message)
            return
        
        blocked = ["connect", "controller", "setup", "config", "admin", "panel", "settings"]
        if any(b in payload.lower() for b in blocked):
            if user_id != Config.ADMIN_ID:
                await send_welcome(message)
                return
        
        movie_code, part, quality, token = decode_payload(payload)
        
        logger.info(f"Decoded: code={movie_code}, part={part}, quality={quality}, token={token[:10] if token else 'None'}...")
        
        if not movie_code:
            await send_welcome(message)
            return
        
        if not await check_subscription(bot, user_id):
            await safe_reply(
                message,
                "🔒 **Join to Continue**\n\n"
                "You must join our channel first.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Join Channel", url=Config.BACKUP_CHANNEL_LINK)],
                    [InlineKeyboardButton("🔄 Try Again", url=f"https://t.me/{bot.me.username}?start={payload}")]
                ]),
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        if token:
            token_data = await db.verify_token(token, user_id)
            
            if token_data:
                movie = await db.get_movie(token_data["movie_code"])
                
                if movie:
                    t_part = token_data.get("part", 1)
                    t_quality = token_data.get("quality", "")
                    
                    file_id = None
                    file_size = ""
                    
                    if t_part > 1 and "parts_data" in movie:
                        part_key = f"part_{t_part}"
                        if part_key in movie["parts_data"]:
                            qualities = movie["parts_data"][part_key].get("qualities", {})
                            if t_quality in qualities:
                                file_id = qualities[t_quality].get("file_id")
                                file_size = qualities[t_quality].get("size", "")
                    else:
                        qualities = movie.get("qualities", {})
                        if t_quality in qualities:
                            file_id = qualities[t_quality].get("file_id")
                            file_size = qualities[t_quality].get("size", "")
                    
                    if file_id:
                        await send_file_with_ads(
                            bot, message, movie, file_id,
                            t_part, t_quality, file_size
                        )
                        return
                
                await safe_reply(message, "❌ File not available. Try searching again.")
                return
            
            await safe_reply(message, "⏰ Link expired! Please search again.")
            return
        
        movie = await db.get_movie(movie_code)
        
        if not movie:
            await send_welcome(message)
            return
        
        if movie.get("parts", 1) > 1:
            buttons = []
            for i in range(1, movie["parts"] + 1):
                buttons.append(InlineKeyboardButton(f"📦 Part {i}", callback_data=f"part:{movie_code}:{i}"))
            
            keyboard = [buttons[i:i+3] for i in range(0, len(buttons), 3)]
            
            await safe_reply(
                message,
                f"🎬 **{movie['title']}**\n\n"
                f"This movie has {movie['parts']} parts.\n"
                f"Select one:",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        qualities = movie.get("qualities", {})
        
        if not qualities:
            await safe_reply(message, "❌ No files available for this movie.")
            return
        
        if len(qualities) == 1:
            quality = list(qualities.keys())[0]
            await generate_download_link(bot, message, movie, 1, quality)
        else:
            await show_quality_selection(message, movie, 1)
    
    
    # ============ /help COMMAND ============
    @app.on_message(filters.command("help") & filters.private)
    async def help_cmd(bot: Client, message: Message):
        user_id = message.from_user.id
        
        text = (
            "🎬 **Movie Bot Help**\n\n"
            "**How to Use:**\n"
            "Just send me a movie name!\n\n"
            "**Examples:**\n"
            "• Kill Bill\n"
            "• Dune\n"
            "• Avengers Endgame"
        )
        
        if user_id == Config.ADMIN_ID:
            text += (
                "\n\n━━━━━━━━━━━━━━━\n"
                "👑 **Admin Commands:**\n\n"
                "`/add Movie Name | quality`\n"
                "`/addpart Movie | part | quality`\n"
                "`/delete Movie Name`\n"
                "`/delete Movie Name | quality`\n"
                "`/list` - List all movies\n"
                "`/stats` - Statistics\n"
                "`/broadcast` - Send to all"
            )
        
        await safe_reply(message, text, parse_mode=ParseMode.MARKDOWN)
    
    
    # ============ SEARCH (any text) ============
    @app.on_message(filters.text & filters.private)
    async def search_cmd(bot: Client, message: Message):
        text = message.text.strip()
        
        if text.startswith("/"):
            return
        
        user_id = message.from_user.id
        await db.add_user(user_id, message.from_user.username)
        
        query = normalize_name(text)
        
        if len(query) < 2:
            await safe_reply(message, "❌ Enter at least 2 characters!")
            return
        
        movies = await db.search_movies(query)
        
        if not movies:
            info = await get_movie_info(text)
            if info:
                await safe_reply(
                    message,
                    f"❌ **Not in database**\n\n"
                    f"Found on TMDB:\n"
                    f"🎬 {info['title']} ({info.get('year', '')})\n"
                    f"⭐ {info.get('rating', 'N/A')}/10\n\n"
                    f"Contact admin to add!",
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await safe_reply(message, "❌ Movie not found! Check spelling.")
            return
        
        if len(movies) == 1:
            await send_movie_card(bot, message, movies[0])
            return
        
        buttons = []
        for m in movies[:10]:
            parts_text = f" ({m.get('parts', 1)} parts)" if m.get('parts', 1) > 1 else ""
            buttons.append([
                InlineKeyboardButton(
                    f"🎬 {m['title']}{parts_text}",
                    callback_data=f"movie:{m['code']}"
                )
            ])
        
        await safe_reply(
            message,
            f"🔍 Found {len(movies)} results:",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=ParseMode.MARKDOWN
        )


# ============ HELPER FUNCTIONS ============

async def send_welcome(message: Message):
    await safe_reply(
        message,
        "🎬 **Welcome to Movie Bot!**\n\n"
        "Send me any movie name to search.\n\n"
        "**Examples:**\n"
        "• Kill Bill\n"
        "• Dune 2021\n"
        "• Avengers Endgame",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Join Channel", url=Config.BACKUP_CHANNEL_LINK)]
        ]),
        parse_mode=ParseMode.MARKDOWN
    )


async def send_movie_card(bot: Client, message: Message, movie: dict):
    info = await get_movie_info(movie["title"])
    
    parts_text = f"\n📦 Parts: {movie['parts']}" if movie.get('parts', 1) > 1 else ""
    
    qualities = movie.get("qualities", {})
    quality_text = ""
    if qualities:
        q_list = []
        for q, data in qualities.items():
            size = data.get("size", "")
            q_list.append(f"{q} ({size})" if size else q)
        quality_text = f"\n🎞️ Available: {', '.join(q_list)}"
    
    if info:
        caption = (
            f"🎬 **{info['title']}** ({info.get('year', '')})\n"
            f"⭐ {info.get('rating', 'N/A')}/10{parts_text}{quality_text}\n\n"
            f"{info.get('overview', '')[:200]}..."
        )
    else:
        caption = f"🎬 **{movie['title']}**{parts_text}{quality_text}"
    
    payload = encode_payload(movie["code"])
    link = f"https://t.me/{bot.me.username}?start={payload}"
    
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("📥 Download", url=link)]])
    
    if info and info.get("poster"):
        try:
            await message.reply_photo(info["poster"], caption=caption, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
            return
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except:
            pass
    
    await safe_reply(message, caption, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)


async def show_quality_selection(message: Message, movie: dict, part: int = 1):
    if part > 1 and "parts_data" in movie:
        part_key = f"part_{part}"
        qualities = movie["parts_data"].get(part_key, {}).get("qualities", {})
    else:
        qualities = movie.get("qualities", {})
    
    if not qualities:
        await safe_reply(message, "❌ No qualities available!")
        return
    
    buttons = []
    for quality, data in qualities.items():
        size = data.get("size", "")
        btn_text = f"🎞️ {quality}" + (f" ({size})" if size else "")
        buttons.append([
            InlineKeyboardButton(btn_text, callback_data=f"quality:{movie['code']}:{part}:{quality}")
        ])
    
    await safe_reply(
        message,
        f"🎬 **{movie['title']}**\n\n"
        f"📦 Part: {part}\n\n"
        f"Select quality:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=ParseMode.MARKDOWN
    )


async def generate_download_link(bot: Client, message: Message, movie: dict, part: int, quality: str):
    user_id = message.from_user.id
    
    token = await db.create_token(user_id, movie["code"], part, quality)
    payload = encode_payload(movie["code"], part, quality, token)
    bot_link = f"https://t.me/{bot.me.username}?start={payload}"
    
    if part > 1 and "parts_data" in movie:
        part_key = f"part_{part}"
        size = movie["parts_data"].get(part_key, {}).get("qualities", {}).get(quality, {}).get("size", "")
    else:
        size = movie.get("qualities", {}).get(quality, {}).get("size", "")
    
    size_text = f"\n📁 Size: {size}" if size else ""
    
    await safe_reply(
        message,
        f"✅ **{movie['title']}**\n\n"
        f"📦 Part: {part}\n"
        f"🎞️ Quality: {quality}{size_text}\n\n"
        f"👇 Click to get file:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📥 Get File", url=bot_link)]
        ]),
        parse_mode=ParseMode.MARKDOWN
    )


async def send_file_with_ads(
    bot: Client,
    message: Message,
    movie: dict,
    file_id: str,
    part: int,
    quality: str,
    file_size: str
):
    user_id = message.from_user.id
    
    status = await safe_reply(message, "🔄 Generating download link...")
    
    if not status:
        return
    
    try:
        file = await bot.get_file(file_id)
        file_url = f"https://api.telegram.org/file/bot{Config.BOT_TOKEN}/{file.file_path}"
        
        file_name = f"{movie['title']} - Part {part} ({quality}).mp4"
        
        download_link = create_download_link(
            file_url=file_url,
            file_name=file_name,
            file_size=file_size,
            quality=quality
        )
        
        await safe_edit(
            status,
            f"✅ **{movie['title']}**\n\n"
            f"📦 Part: {part}\n"
            f"🎞️ Quality: {quality}\n"
            f"📁 Size: {file_size}\n\n"
            f"👇 **Click to Download:**\n\n"
            f"⚠️ _Link expires in 1 hour_",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬇️ Download Movie", url=download_link)]
            ]),
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        logger.error(f"Ad page error: {e}")
        
        try:
            await status.delete()
        except:
            pass
        
        try:
            await bot.send_cached_media(
                chat_id=user_id,
                file_id=file_id,
                caption=(
                    f"🎬 **{movie['title']}**\n\n"
                    f"📦 Part: {part}\n"
                    f"🎞️ Quality: {quality}\n\n"
                    f"✅ Enjoy!"
                ),
                parse_mode=ParseMode.MARKDOWN
            )
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except:
            await message.reply_document(
                file_id,
                caption=f"🎬 **{movie['title']}** ({quality})",
                parse_mode=ParseMode.MARKDOWN
            )
