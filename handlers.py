from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ForceReply
from video_processor import generate_clips
from gemini_integration import generate_caption
import os
import asyncio

# A dictionary to store temporary settings for each user
user_settings = {}

def setup_handlers(app: Client):
    """
    Sets up all the message and callback query handlers for the bot.
    """
    @app.on_message(filters.video & filters.private)
    async def receive_video(client, message):
        user_id = message.from_user.id
        
        # Download the video and store the path in user settings
        status_message = await message.reply_text("✅ Video received! Downloading...")
        file_path = await message.download(file_name=f"videos/{user_id}.mp4")
        user_settings[user_id] = {"video_path": file_path}
        
        await status_message.edit_text(
            "✅ Video downloaded! Please choose your settings:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⏱ Clip Duration", callback_data="duration")],
                [InlineKeyboardButton("📏 Aspect Ratio", callback_data="ratio")],
                [InlineKeyboardButton("🎬 Clip Count", callback_data="clip_count")],
                [InlineKeyboardButton("💧 Watermark", callback_data="watermark")],
                [InlineKeyboardButton("✅ Generate Shorts", callback_data="generate")],
            ])
        )

    @app.on_message(filters.text & filters.private & filters.regex(r"^\d+$"))
    async def handle_custom_clip_count(client, message):
        user_id = message.from_user.id
        if user_id in user_settings and user_settings[user_id].get("awaiting_custom_count"):
            try:
                count = int(message.text)
                user_settings[user_id]["clip_count"] = count
                user_settings[user_id]["awaiting_custom_count"] = False
                await message.reply_text(f"🎬 Custom clip count set to {count}. You can now generate shorts.")
            except ValueError:
                await message.reply_text("That's not a valid number. Please send a number for the custom clip count.")

    @app.on_callback_query()
    async def handle_query(client, callback_query):
        user_id = callback_query.from_user.id
        data = callback_query.data
        
        await callback_query.answer() # Answer the query to remove the loading animation

        if user_id not in user_settings:
            await callback_query.message.reply_text("Please send a video first to begin.")
            return

        if data == "duration":
            await callback_query.message.edit_text(
                "⏱ Choose a clip duration:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"{x}s", callback_data=f"duration:{x}") for x in ["20", "30", "59"]],
                    [InlineKeyboardButton(f"{x}s", callback_data=f"duration:{x}") for x in ["90", "120", "180"]],
                    [InlineKeyboardButton("⬅️ Back", callback_data="back_to_main")],
                ])
            )
        elif data.startswith("duration:"):
            duration = int(data.split(":")[1])
            user_settings[user_id]["duration"] = duration
            await callback_query.message.edit_text(f"⏱ Duration set to {duration} seconds. What's next?", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back_to_main")]]))

        elif data == "ratio":
            await callback_query.message.edit_text(
                "📏 Choose an aspect ratio:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Original", callback_data="ratio:original")],
                    [InlineKeyboardButton("9:16 (Shorts)", callback_data="ratio:9:16"), InlineKeyboardButton("1:1 (Square)", callback_data="ratio:1:1")],
                    [InlineKeyboardButton("4:3", callback_data="ratio:4:3"), InlineKeyboardButton("16:9 (Horizontal)", callback_data="ratio:16:9")],
                    [InlineKeyboardButton("⬅️ Back", callback_data="back_to_main")],
                ])
            )
        elif data.startswith("ratio:"):
            ratio = data.split(":")[1]
            user_settings[user_id]["ratio"] = ratio
            await callback_query.message.edit_text(f"📏 Ratio set to {ratio}. What's next?", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back_to_main")]]))

        elif data == "clip_count":
            await callback_query.message.edit_text(
                "🎬 Choose the number of clips:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(str(x), callback_data=f"clip_count:{x}") for x in [2, 5, 8, 10]],
                    [InlineKeyboardButton("Custom", callback_data="clip_count:custom")],
                    [InlineKeyboardButton("⬅️ Back", callback_data="back_to_main")],
                ])
            )
        elif data.startswith("clip_count:"):
            count = data.split(":")[1]
            if count == "custom":
                user_settings[user_id]["awaiting_custom_count"] = True
                await callback_query.message.edit_text("🔢 Please send a number for the custom clip count.")
            else:
                user_settings[user_id]["clip_count"] = int(count)
                await callback_query.message.edit_text(f"🎬 Clip count set to {count}. What's next?", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back_to_main")]]))

        elif data == "watermark":
            await callback_query.message.edit_text(
                "💧 Choose watermark position:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Top Left", callback_data="wm:tl"), InlineKeyboardButton("Top Right", callback_data="wm:tr")],
                    [InlineKeyboardButton("Bottom Left", callback_data="wm:bl"), InlineKeyboardButton("Bottom Right", callback_data="wm:br")],
                    [InlineKeyboardButton("⬅️ Back", callback_data="back_to_main")],
                ])
            )
        elif data.startswith("wm:"):
            watermark_pos = data.split(":")[1]
            user_settings[user_id]["watermark"] = watermark_pos
            await callback_query.message.edit_text(f"💧 Watermark position set. What's next?", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back_to_main")]]))

        elif data == "back_to_main":
            await callback_query.message.edit_text(
                "✅ Video received! Please choose your settings:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⏱ Clip Duration", callback_data="duration")],
                    [InlineKeyboardButton("📏 Aspect Ratio", callback_data="ratio")],
                    [InlineKeyboardButton("🎬 Clip Count", callback_data="clip_count")],
                    [InlineKeyboardButton("💧 Watermark", callback_data="watermark")],
                    [InlineKeyboardButton("✅ Generate Shorts", callback_data="generate")],
                ])
            )

        elif data == "generate":
            await callback_query.message.reply_text("🚀 Starting to generate your shorts. This might take a few moments...")
            
            opts = user_settings[user_id]
            clips = generate_clips(
                opts["video_path"],
                duration=opts.get("duration", 30),
                ratio=opts.get("ratio", "9:16"), # Default to 9:16 if not set
                clip_count=opts.get("clip_count", 5),
                watermark_pos=opts.get("watermark", "tr")
            )
            
            if clips:
                for clip_path in clips:
                    # Generate a caption for each clip
                    caption_text = generate_caption({"duration": opts.get("duration", 30)})
                    await client.send_video(callback_query.message.chat.id, video=clip_path, caption=caption_text)
                    os.remove(clip_path) # Clean up the generated clip file
                
                await callback_query.message.reply_text("✅ All shorts generated successfully! Files have been cleaned up.")
                
            else:
                await callback_query.message.reply_text("⚠️ An error occurred while generating the shorts. Please try again.")

            # Clean up the original video file and user settings
            if "video_path" in user_settings[user_id]:
                os.remove(user_settings[user_id]["video_path"])
                del user_settings[user_id]

