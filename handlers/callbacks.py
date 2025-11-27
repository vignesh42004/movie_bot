if __name__ == "__main__":
    exit("Run bot.py instead!")

import logging
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from config import Config
from database import db
from helpers import check_subscription, get_short_link, encode_payload, get_movie_info

logger = logging.getLogger(__name__)


def register_callback_handlers(app: Client):
    
    # ============ MOVIE SELECTION ============
    @app.on_callback_query(filters.regex(r"^movie:"))
    async def movie_cb(bot: Client, query: CallbackQuery):
        code = query.data.split(":")[1]
        movie = await db.get_movie(code)
        
        if not movie:
            await query.answer("❌ Not found!", show_alert=True)
            return
        
        # Check if multi-part
        if movie.get("parts", 1) > 1:
            buttons = []
            for i in range(1, movie["parts"] + 1):
                buttons.append(InlineKeyboardButton(f"📦 Part {i}", callback_data=f"part:{code}:{i}"))
            
            keyboard = [buttons[i:i+3] for i in range(0, len(buttons), 3)]
            
            await query.message.edit_text(
                f"🎬 **{movie['title']}**\n\n"
                f"This movie has {movie['parts']} parts.\n"
                f"Select one:",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            # Show quality selection
            await show_quality_buttons(query, movie, 1)
        
        await query.answer()
    
    
    # ============ PART SELECTION ============
    @app.on_callback_query(filters.regex(r"^part:"))
    async def part_cb(bot: Client, query: CallbackQuery):
        _, code, part = query.data.split(":")
        part = int(part)
        
        movie = await db.get_movie(code)
        if not movie:
            await query.answer("❌ Not found!", show_alert=True)
            return
        
        # Show quality selection for this part
        await show_quality_buttons(query, movie, part)
        await query.answer()
    
    
    # ============ QUALITY SELECTION ============
    @app.on_callback_query(filters.regex(r"^quality:"))
    async def quality_cb(bot: Client, query: CallbackQuery):
        user_id = query.from_user.id
        parts = query.data.split(":")
        code = parts[1]
        part = int(parts[2])
        quality = parts[3]
        
        # Check subscription
        if not await check_subscription(bot, user_id):
            await query.answer("❌ Join channel first!", show_alert=True)
            return
        
        movie = await db.get_movie(code)
        if not movie:
            await query.answer("❌ Not found!", show_alert=True)
            return
        
        # Generate download link
        token = await db.create_token(user_id, code, part, quality)
        payload = encode_payload(code, part, quality, token)
        final_link = f"https://t.me/{bot.me.username}?start={payload}"
        
        await query.answer("🔄 Generating link...")
        
        short_link = await get_short_link(final_link)
        
        # Get file size
        if part > 1 and "parts_data" in movie:
            part_key = f"part_{part}"
            size = movie["parts_data"].get(part_key, {}).get("qualities", {}).get(quality, {}).get("size", "")
        else:
            size = movie.get("qualities", {}).get(quality, {}).get("size", "")
        
        size_text = f"\n📁 Size: {size}" if size else ""
        
        # Back button
        if movie.get("parts", 1) > 1:
            back_btn = InlineKeyboardButton("◀️ Back to Parts", callback_data=f"movie:{code}")
        else:
            back_btn = InlineKeyboardButton("◀️ Back", callback_data=f"backq:{code}:{part}")
        
        await query.message.edit_text(
            f"✅ **{movie['title']}**\n\n"
            f"📦 Part: {part}\n"
            f"🎞️ Quality: {quality}{size_text}\n\n"
            f"👇 Click to download:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔓 Download", url=short_link)],
                [back_btn]
            ]),
            parse_mode=ParseMode.MARKDOWN
        )
    
    
    # ============ BACK TO QUALITY SELECTION ============
    @app.on_callback_query(filters.regex(r"^backq:"))
    async def back_quality_cb(bot: Client, query: CallbackQuery):
        _, code, part = query.data.split(":")
        part = int(part)
        
        movie = await db.get_movie(code)
        if not movie:
            await query.answer("❌ Not found!", show_alert=True)
            return
        
        await show_quality_buttons(query, movie, part)
        await query.answer()


# ============ HELPER FUNCTION ============

async def show_quality_buttons(query: CallbackQuery, movie: dict, part: int):
    """Show quality selection buttons"""
    
    if part > 1 and "parts_data" in movie:
        part_key = f"part_{part}"
        qualities = movie["parts_data"].get(part_key, {}).get("qualities", {})
    else:
        qualities = movie.get("qualities", {})
    
    if not qualities:
        await query.message.edit_text(
            f"❌ No files available for **{movie['title']}** Part {part}",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    buttons = []
    for quality, data in qualities.items():
        size = data.get("size", "")
        btn_text = f"🎞️ {quality}" + (f" ({size})" if size else "")
        buttons.append([
            InlineKeyboardButton(btn_text, callback_data=f"quality:{movie['code']}:{part}:{quality}")
        ])
    
    # Add back button if multi-part
    if movie.get("parts", 1) > 1:
        buttons.append([InlineKeyboardButton("◀️ Back to Parts", callback_data=f"movie:{movie['code']}")])
    
    await query.message.edit_text(
        f"🎬 **{movie['title']}**\n\n"
        f"📦 Part: {part}\n\n"
        f"Select quality:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=ParseMode.MARKDOWN
    )