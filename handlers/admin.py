if __name__ == "__main__":
    exit("Run bot.py instead!")

import logging
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import Config
from database import db
from helpers import normalize_name, check_subscription

logger = logging.getLogger(__name__)

# Available quality options
QUALITY_OPTIONS = ["360p", "480p", "720p", "1080p", "1440p", "2160p", "4K"]


def register_admin_handlers(app: Client):
    
    # ============ /add COMMAND ============
    @app.on_message(filters.command("add") & filters.private & filters.user(Config.ADMIN_ID))
    async def add_movie(bot: Client, message: Message):
        """
        Add movie with quality
        Usage: /add Movie Name | quality
        Example: /add Kill Bill Part 1 | 720p
        Example: /add Dune 2021 | 1080p
        """
        
        if not message.reply_to_message:
            await message.reply_text(
                "📥 **How to Add Movie:**\n\n"
                "1️⃣ Send/forward a video file\n"
                "2️⃣ Reply to it with:\n\n"
                "`/add Movie Name | quality`\n\n"
                "**Examples:**\n"
                "`/add Kill Bill Part 1 | 720p`\n"
                "`/add Dune 2021 | 1080p`\n"
                "`/add Avengers Endgame | 480p`\n\n"
                "**Available Qualities:**\n"
                "360p, 480p, 720p, 1080p, 1440p, 2160p, 4K",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        replied = message.reply_to_message
        file_id = None
        file_size = 0
        
        if replied.video:
            file_id = replied.video.file_id
            file_size = replied.video.file_size or 0
        elif replied.document:
            file_id = replied.document.file_id
            file_size = replied.document.file_size or 0
        
        if not file_id:
            await message.reply_text("❌ Reply to a video or document file!")
            return
        
        # Parse command: /add Movie Name | quality
        text = message.text.replace("/add", "").strip()
        
        if not text:
            await message.reply_text(
                "❌ **Please provide movie name and quality!**\n\n"
                "Format: `/add Movie Name | quality`\n"
                "Example: `/add Kill Bill Part 1 | 720p`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Split by | to get title and quality
        if "|" in text:
            parts = text.split("|")
            title = parts[0].strip()
            quality = parts[1].strip().lower()
        else:
            # No quality specified, ask user
            await message.reply_text(
                "❌ **Please specify quality!**\n\n"
                "Format: `/add Movie Name | quality`\n"
                "Example: `/add Kill Bill Part 1 | 720p`\n\n"
                "**Available:** 360p, 480p, 720p, 1080p, 1440p, 2160p, 4K",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Validate quality
        quality = quality.upper() if quality.upper() == "4K" else quality.lower()
        valid_qualities = [q.lower() for q in QUALITY_OPTIONS]
        
        if quality.lower() not in valid_qualities and quality != "4K":
            await message.reply_text(
                f"❌ **Invalid quality:** `{quality}`\n\n"
                f"**Available:** {', '.join(QUALITY_OPTIONS)}",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        if not title:
            await message.reply_text("❌ Movie title cannot be empty!")
            return
        
        # Generate code from title (lowercase, spaces to underscores)
        code = normalize_name(title).replace(" ", "_")
        
        # Format file size
        size_mb = round(file_size / (1024 * 1024), 2) if file_size else 0
        size_text = f"{size_mb} MB" if size_mb < 1024 else f"{round(size_mb/1024, 2)} GB"
        
        # Check if movie exists
        existing = await db.get_movie(code)
        
        if existing:
            # Add quality to existing movie
            qualities = existing.get("qualities", {})
            qualities[quality] = {
                "file_id": file_id,
                "size": size_text
            }
            existing["qualities"] = qualities
            await db.add_movie(existing)
            
            available = ", ".join(qualities.keys())
            await message.reply_text(
                f"✅ **Quality Added to Existing Movie!**\n\n"
                f"📽️ **Title:** {existing['title']}\n"
                f"🔑 **Code:** `{code}`\n"
                f"🎞️ **New Quality:** {quality} ({size_text})\n"
                f"📦 **All Qualities:** {available}",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            # Create new movie
            movie_data = {
                "code": code,
                "title": title,
                "qualities": {
                    quality: {
                        "file_id": file_id,
                        "size": size_text
                    }
                },
                "parts": 1
            }
            await db.add_movie(movie_data)
            
            await message.reply_text(
                f"✅ **Movie Added!**\n\n"
                f"📽️ **Title:** {title}\n"
                f"🔑 **Code:** `{code}`\n"
                f"🎞️ **Quality:** {quality} ({size_text})\n\n"
                f"💡 Add more qualities by replying to another file with:\n"
                f"`/add {title} | 480p`",
                parse_mode=ParseMode.MARKDOWN
            )
    
    
    # ============ /addpart COMMAND ============
    @app.on_message(filters.command("addpart") & filters.private & filters.user(Config.ADMIN_ID))
    async def add_part(bot: Client, message: Message):
        """
        Add part to existing movie with quality
        Usage: /addpart Movie Name | part | quality
        Example: /addpart Kill Bill | 2 | 720p
        """
        
        if not message.reply_to_message:
            await message.reply_text(
                "📥 **How to Add Movie Part:**\n\n"
                "1️⃣ Send/forward Part 2 video\n"
                "2️⃣ Reply to it with:\n\n"
                "`/addpart Movie Name | part_number | quality`\n\n"
                "**Examples:**\n"
                "`/addpart Kill Bill | 2 | 720p`\n"
                "`/addpart Dune | 2 | 1080p`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        replied = message.reply_to_message
        file_id = None
        file_size = 0
        
        if replied.video:
            file_id = replied.video.file_id
            file_size = replied.video.file_size or 0
        elif replied.document:
            file_id = replied.document.file_id
            file_size = replied.document.file_size or 0
        
        if not file_id:
            await message.reply_text("❌ Reply to a video or document file!")
            return
        
        # Parse: /addpart Movie Name | part | quality
        text = message.text.replace("/addpart", "").strip()
        
        if "|" not in text or text.count("|") < 2:
            await message.reply_text(
                "❌ **Wrong format!**\n\n"
                "Use: `/addpart Movie Name | part_number | quality`\n"
                "Example: `/addpart Kill Bill | 2 | 720p`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        parts = text.split("|")
        title = parts[0].strip()
        
        try:
            part_num = int(parts[1].strip())
        except:
            await message.reply_text("❌ Part number must be a number!")
            return
        
        quality = parts[2].strip().lower()
        quality = quality.upper() if quality.upper() == "4K" else quality.lower()
        
        # Validate quality
        valid_qualities = [q.lower() for q in QUALITY_OPTIONS]
        if quality.lower() not in valid_qualities and quality != "4K":
            await message.reply_text(
                f"❌ **Invalid quality:** `{quality}`\n\n"
                f"**Available:** {', '.join(QUALITY_OPTIONS)}",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        code = normalize_name(title).replace(" ", "_")
        
        # Format file size
        size_mb = round(file_size / (1024 * 1024), 2) if file_size else 0
        size_text = f"{size_mb} MB" if size_mb < 1024 else f"{round(size_mb/1024, 2)} GB"
        
        # Get or create movie
        movie = await db.get_movie(code)
        
        if not movie:
            movie = {
                "code": code,
                "title": title,
                "qualities": {},
                "parts": part_num,
                "parts_data": {}
            }
        
        # Initialize parts_data if not exists
        if "parts_data" not in movie:
            movie["parts_data"] = {}
        
        # Add part with quality
        part_key = f"part_{part_num}"
        if part_key not in movie["parts_data"]:
            movie["parts_data"][part_key] = {"qualities": {}}
        
        movie["parts_data"][part_key]["qualities"][quality] = {
            "file_id": file_id,
            "size": size_text
        }
        
        # Update parts count
        movie["parts"] = max(movie.get("parts", 1), part_num)
        
        await db.add_movie(movie)
        
        available_qualities = ", ".join(movie["parts_data"][part_key]["qualities"].keys())
        
        await message.reply_text(
            f"✅ **Part {part_num} Added!**\n\n"
            f"📽️ **Movie:** {title}\n"
            f"📦 **Part:** {part_num}\n"
            f"🎞️ **Quality:** {quality} ({size_text})\n"
            f"📦 **Total Parts:** {movie['parts']}\n"
            f"🎞️ **Part {part_num} Qualities:** {available_qualities}",
            parse_mode=ParseMode.MARKDOWN
        )
    
    
    # ============ /delete COMMAND ============
    @app.on_message(filters.command("delete") & filters.private & filters.user(Config.ADMIN_ID))
    async def delete_movie(bot: Client, message: Message):
        """Delete movie or specific quality"""
        
        text = message.text.replace("/delete", "").strip()
        
        if not text:
            await message.reply_text(
                "❌ **How to Delete:**\n\n"
                "Delete entire movie:\n"
                "`/delete Movie Name`\n\n"
                "Delete specific quality:\n"
                "`/delete Movie Name | quality`\n\n"
                "**Examples:**\n"
                "`/delete Kill Bill Part 1`\n"
                "`/delete Dune 2021 | 720p`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        if "|" in text:
            # Delete specific quality
            parts = text.split("|")
            title = parts[0].strip()
            quality = parts[1].strip().lower()
            quality = quality.upper() if quality.upper() == "4K" else quality
            
            code = normalize_name(title).replace(" ", "_")
            movie = await db.get_movie(code)
            
            if not movie:
                await message.reply_text(f"❌ Movie `{title}` not found!", parse_mode=ParseMode.MARKDOWN)
                return
            
            qualities = movie.get("qualities", {})
            if quality in qualities:
                del qualities[quality]
                movie["qualities"] = qualities
                
                if not qualities:
                    # No qualities left, delete movie
                    await db.delete_movie(code)
                    await message.reply_text(f"✅ `{title}` deleted (no qualities left)!", parse_mode=ParseMode.MARKDOWN)
                else:
                    await db.add_movie(movie)
                    await message.reply_text(
                        f"✅ **Quality `{quality}` removed from `{title}`!**\n\n"
                        f"Remaining: {', '.join(qualities.keys())}",
                        parse_mode=ParseMode.MARKDOWN
                    )
            else:
                await message.reply_text(f"❌ Quality `{quality}` not found!", parse_mode=ParseMode.MARKDOWN)
        else:
            # Delete entire movie
            code = normalize_name(text).replace(" ", "_")
            
            if await db.delete_movie(code):
                await message.reply_text(f"✅ `{text}` deleted!", parse_mode=ParseMode.MARKDOWN)
            else:
                await message.reply_text(f"❌ `{text}` not found!", parse_mode=ParseMode.MARKDOWN)
    
    
    # ============ /list COMMAND ============
    @app.on_message(filters.command("list") & filters.private & filters.user(Config.ADMIN_ID))
    async def list_movies(bot: Client, message: Message):
        movies = await db.get_all_movies()
        
        if not movies:
            await message.reply_text("📭 No movies yet!")
            return
        
        text = "📽️ **All Movies:**\n\n"
        
        for i, m in enumerate(movies[:50], 1):
            qualities = m.get("qualities", {})
            quality_list = ", ".join(qualities.keys()) if qualities else "No qualities"
            parts = m.get("parts", 1)
            parts_text = f" ({parts} parts)" if parts > 1 else ""
            
            text += f"{i}. **{m['title']}**{parts_text}\n"
            text += f"   Code: `{m['code']}`\n"
            text += f"   Qualities: {quality_list}\n\n"
        
        if len(movies) > 50:
            text += f"\n_...and {len(movies) - 50} more_"
        
        await message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    
    # ============ /stats COMMAND ============
    @app.on_message(filters.command("stats") & filters.private & filters.user(Config.ADMIN_ID))
    async def stats(bot: Client, message: Message):
        users = await db.get_user_count()
        movies = await db.get_all_movies()
        
        total_qualities = 0
        for m in movies:
            total_qualities += len(m.get("qualities", {}))
        
        await message.reply_text(
            f"📊 **Bot Statistics**\n\n"
            f"👥 Users: {users}\n"
            f"🎬 Movies: {len(movies)}\n"
            f"🎞️ Total Files: {total_qualities}",
            parse_mode=ParseMode.MARKDOWN
        )
    
    
    # ============ /broadcast COMMAND ============
    @app.on_message(filters.command("broadcast") & filters.private & filters.user(Config.ADMIN_ID))
    async def broadcast(bot: Client, message: Message):
        if not message.reply_to_message:
            await message.reply_text("❌ Reply to a message to broadcast!")
            return
        
        users = await db.get_all_users()
        sent, failed = 0, 0
        
        status = await message.reply_text("📢 Broadcasting...")
        
        for user in users:
            try:
                await message.reply_to_message.copy(user["user_id"])
                sent += 1
            except:
                failed += 1
        
        await status.edit_text(f"📢 **Done!**\n\n✅ Sent: {sent}\n❌ Failed: {failed}", parse_mode=ParseMode.MARKDOWN)
    
    
    # ============ /checksub COMMAND ============
    @app.on_message(filters.command("checksub") & filters.private & filters.user(Config.ADMIN_ID))
    async def checksub(bot: Client, message: Message):
        user_id = message.from_user.id
        is_sub = await check_subscription(bot, user_id)
        
        await message.reply_text(
            f"🔍 **Debug Info**\n\n"
            f"Channel ID: `{Config.BACKUP_CHANNEL_ID}`\n"
            f"Your Status: {'✅ Subscribed' if is_sub else '❌ Not Subscribed'}",
            parse_mode=ParseMode.MARKDOWN
        )