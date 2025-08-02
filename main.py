
import os
import subprocess
import shlex
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import sys

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient
import google.generativeai as genai


# ===================================
API_ID = 27356561
API_HASH = "efa4696acce7444105b02d82d0b2e381"
BOT_TOKEN = "8009058333:AAHiF0BsNTpK2YrMEUhhvltwEHRAGWfktCs"
GEMINI_API_KEY = "AIzaSyDelpeEYkt1M_grzmvvcmFoKnlaCG_E2fY"

ADMIN_ID = 6644681404

MONGO_URI = "mongodb+srv://cristi7jjr:tRjSVaoSNQfeZ0Ik@cluster0.kowid.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
COLLECTION_NAME = "shortsTom"

# === 2. Database and AI Setup ===
try:
    mongo_client = MongoClient(MONGO_URI)
    db = mongo_client.get_database()
    shorts_collection = db[COLLECTION_NAME]
    print("Successfully connected to MongoDB!")
except Exception as e:
    print(f"Failed to connect to MongoDB: {e}")
    sys.exit(1)

genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel('gemini-pro')

# === 3. Helper Functions ===
def get_user_settings(user_id):
    """Retrieves or creates user settings and stats from MongoDB."""
    user = shorts_collection.find_one({"_id": user_id})
    if user is None:
        default_settings = {
            "_id": user_id,
            "video_path": None,
            "duration": 30,
            "ratio": "9:16",
            "clip_count": 5,
            "watermark": "tr",
            "awaiting_custom_count": False,
            "stats": {
                "videos_processed": 0,
                "shorts_generated": 0,
                "uploads_sent": 0,
            }
        }
        shorts_collection.insert_one(default_settings)
        return default_settings
    return user

def update_user_settings(user_id, key, value):
    """Updates a single setting for a user in MongoDB."""
    shorts_collection.update_one({"_id": user_id}, {"$set": {key: value}})

def update_user_stats(user_id, stat_key, increment=1):
    """Increments a user's stat count."""
    shorts_collection.update_one({"_id": user_id}, {"$inc": {f"stats.{stat_key}": increment}})

def get_video_metadata(video_path):
    """Get video duration using ffprobe."""
    try:
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", video_path]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        metadata = json.loads(result.stdout)
        duration = float(metadata['format']['duration'])
        return duration
    except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error getting video metadata: {e}")
        return None

def generate_caption(video_info):
    """Generates a viral caption using the Gemini API."""
    duration = video_info.get("duration", "30")
    prompt = f"You're an AI shorts caption creator. The user sent a {duration}-second clip. Give a viral caption under 80 characters, emotional and trendy. Respond only with the final caption."
    try:
        response = gemini_model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Error generating caption: {e}")
        return "Check out this awesome short!"

def generate_clips(video_path, settings):
    """
    Generates multiple video clips with specified settings using FFmpeg.
    """
    clips = []
    total_duration = get_video_metadata(video_path)
    if total_duration is None:
        return []

    output_dir = "generated_clips"
    os.makedirs(output_dir, exist_ok=True)
    
    # FFmpeg commands based on settings
    duration = settings.get("duration", 30)
    ratio = settings.get("ratio", "9:16")
    clip_count = settings.get("clip_count", 5)
    watermark_pos = settings.get("watermark", "tr")

    # [More advanced features logic would go here, e.g., OpenCV tracking]
    # For now, these are just placeholders for the user UI buttons
    # if settings.get("auto_tracking"):
    #     ...
    
    # [FFmpeg logic for cropping and watermarking]
    if ratio == "9:16": crop_filter = "crop=ih*9/16:ih"
    elif ratio == "1:1": crop_filter = "crop=ih:ih"
    elif ratio == "4:3": crop_filter = "crop=ih*4/3:ih"
    else: crop_filter = "crop=iw:ih" # 16:9 or original
    
    watermark_text = "Your Watermark"
    if watermark_pos == "tr": watermark_pos = "x=w-tw-10:y=10"
    elif watermark_pos == "tl": watermark_pos = "x=10:y=10"
    elif watermark_pos == "bl": watermark_pos = "x=10:y=h-th-10"
    elif watermark_pos == "br": watermark_pos = "x=w-tw-10:y=h-th-10"

    intervals = (total_duration - duration) // clip_count if total_duration > duration else 0

    for i in range(clip_count):
        start_time = i * intervals
        output_file = os.path.join(output_dir, f"clip_{i}.mp4")
        
        ffmpeg_cmd = [
            "ffmpeg", "-ss", str(start_time), "-i", video_path, "-t", str(duration),
            "-vf", f"{crop_filter},drawtext=text='{watermark_text}':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:{watermark_pos}:fontsize=50:fontcolor=white@0.8",
            "-c:a", "copy", output_file, "-y"
        ]
        
        try:
            print(f"Running FFmpeg command: {' '.join(ffmpeg_cmd)}")
            subprocess.run(ffmpeg_cmd, check=True)
            clips.append(output_file)
        except subprocess.CalledProcessError as e:
            print(f"Error processing video: {e}")
            
    return clips


# === 4. Bot Handlers ===
app = Client("shorts_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def get_main_menu_markup():
    """Returns the main inline keyboard markup."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⏱ Clip Duration", callback_data="duration")],
        [InlineKeyboardButton("📏 Aspect Ratio", callback_data="ratio")],
        [InlineKeyboardButton("🎬 Clip Count", callback_data="clip_count")],
        [InlineKeyboardButton("💧 Watermark", callback_data="watermark")],
        [InlineKeyboardButton("🤖 Advanced Features", callback_data="advanced_features")],
        [InlineKeyboardButton("✅ Generate Shorts", callback_data="generate")],
    ])

# Admin panel keyboard
def get_admin_panel_markup():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Bot Stats", callback_data="admin_stats")],
        [InlineKeyboardButton("⚙️ Admin Settings", callback_data="admin_settings")],
        [InlineKeyboardButton("👥 Manage Users", callback_data="admin_manage_users")],
    ])

@app.on_message(filters.video & filters.private)
async def receive_video(client, message):
    user_id = message.from_user.id
    
    # Check if the user is in the database and get settings
    user_data = get_user_settings(user_id)
    
    status_message = await message.reply_text("✅ Video received! Downloading...")
    file_path = await message.download(file_name=f"videos/{user_id}.mp4")
    
    update_user_settings(user_id, "video_path", file_path)
    update_user_stats(user_id, "videos_processed")
    
    await status_message.edit_text(
        "✅ Video downloaded! Please choose your settings:",
        reply_markup=get_main_menu_markup()
    )

@app.on_message(filters.command("admin") & filters.private)
async def admin_panel(client, message):
    if message.from_user.id == ADMIN_ID:
        await message.reply_text(
            "Welcome to the Admin Panel!",
            reply_markup=get_admin_panel_markup()
        )
    else:
        await message.reply_text("You are not authorized to access this panel.")


@app.on_message(filters.text & filters.private & filters.regex(r"^\d+$"))
async def handle_custom_clip_count(client, message):
    user_id = message.from_user.id
    user_data = get_user_settings(user_id)
    if user_data.get("awaiting_custom_count"):
        try:
            count = int(message.text)
            update_user_settings(user_id, "clip_count", count)
            update_user_settings(user_id, "awaiting_custom_count", False)
            await message.reply_text(f"🎬 Custom clip count set to {count}. You can now generate shorts.")
        except ValueError:
            await message.reply_text("That's not a valid number. Please send a number for the custom clip count.")

@app.on_callback_query()
async def handle_query(client, callback_query):
    user_id = callback_query.from_user.id
    data = callback_query.data
    await callback_query.answer()

    user_data = get_user_settings(user_id)
    if user_data.get("video_path") is None and not data.startswith("admin_"):
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
        update_user_settings(user_id, "duration", duration)
        await callback_query.message.edit_text(f"⏱ Duration set to {duration}s. What's next?", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back_to_main")]]))

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
        update_user_settings(user_id, "ratio", ratio)
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
            update_user_settings(user_id, "awaiting_custom_count", True)
            await callback_query.message.edit_text("🔢 Please send a number for the custom clip count.")
        else:
            update_user_settings(user_id, "clip_count", int(count))
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
        update_user_settings(user_id, "watermark", watermark_pos)
        await callback_query.message.edit_text(f"💧 Watermark position set. What's next?", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back_to_main")]]))
    
    elif data == "advanced_features":
        await callback_query.message.edit_text(
            "🤖 Choose an advanced feature:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎯 Auto-tracking", callback_data="feature:autotrack")],
                [InlineKeyboardButton("🧠 Smart Cuts", callback_data="feature:smartcuts")],
                [InlineKeyboardButton("⬅️ Back", callback_data="back_to_main")],
            ])
        )
    elif data.startswith("feature:"):
        feature = data.split(":")[1]
        update_user_settings(user_id, "advanced_feature", feature)
        await callback_query.message.edit_text(f"🤖 Advanced feature '{feature}' enabled. What's next?", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back_to_main")]]))

    elif data == "back_to_main":
        await callback_query.message.edit_text("Please choose your settings:", reply_markup=get_main_menu_markup())

    elif data == "generate":
        await callback_query.message.reply_text("🚀 Starting to generate your shorts. This might take a few moments...")
        
        opts = get_user_settings(user_id)
        clips = generate_clips(opts.get("video_path"), opts)
        
        if clips:
            for clip_path in clips:
                caption_text = generate_caption({"duration": opts.get("duration", 30)})
                await client.send_video(callback_query.message.chat.id, video=clip_path, caption=caption_text)
                os.remove(clip_path)
            
            update_user_stats(user_id, "shorts_generated", len(clips))
            update_user_stats(user_id, "uploads_sent", len(clips))
            
            await callback_query.message.reply_text("✅ All shorts generated successfully! Files have been cleaned up.")
        else:
            await callback_query.message.reply_text("⚠️ An error occurred while generating the shorts. Please try again.")

        if opts.get("video_path") and os.path.exists(opts["video_path"]):
            os.remove(opts["video_path"])
        update_user_settings(user_id, "video_path", None)
        
    elif data == "admin_stats" and user_id == ADMIN_ID:
        total_users = shorts_collection.count_documents({})
        total_videos = shorts_collection.aggregate([{"$group": {"_id": None, "total": {"$sum": "$stats.videos_processed"}}}])
        total_shorts = shorts_collection.aggregate([{"$group": {"_id": None, "total": {"$sum": "$stats.shorts_generated"}}}])
        
        stats = {
            "Total Users": total_users,
            "Total Videos Processed": list(total_videos)[0]["total"] if list(total_videos) else 0,
            "Total Shorts Generated": list(total_shorts)[0]["total"] if list(total_shorts) else 0,
        }
        stats_text = "\n".join([f"{k}: {v}" for k, v in stats.items()])
        await callback_query.message.edit_text(f"📊 **Bot Statistics**\n\n{stats_text}", reply_markup=get_admin_panel_markup())
        
    elif data == "admin_manage_users" and user_id == ADMIN_ID:
        users = shorts_collection.find({}, {"_id": 1, "stats.shorts_generated": 1, "stats.videos_processed": 1}).sort("_id", 1).limit(10)
        user_list = "👥 **Top 10 Users**\n\n"
        for user in users:
            user_list += f"ID: `{user['_id']}`\n  Shorts: {user['stats']['shorts_generated']}\n  Videos: {user['stats']['videos_processed']}\n\n"
        await callback_query.message.edit_text(user_list, reply_markup=get_admin_panel_markup())

# === 5. Health Check Server ===
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Bot is running")

def run_health_check_server():
    server = HTTPServer(('0.0.0.0', 8080), HealthCheckHandler)
    print("Health check server started on port 8080.")
    server.serve_forever()

# === 6. Main execution block ===
if __name__ == '__main__':
    os.makedirs("videos", exist_ok=True)
    os.makedirs("generated_clips", exist_ok=True)
    
    health_thread = threading.Thread(target=run_health_check_server, daemon=True)
    health_thread.start()

    print("Starting bot...")
    try:
        app.run()
    except Exception as e:
        print(f"An error occurred during bot startup: {e}")
        sys.exit(1)

