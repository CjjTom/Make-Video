from pyrogram import Client
from config import API_ID, API_HASH, BOT_TOKEN
from handlers import setup_handlers
import os

# Create a directory to store videos
if not os.path.exists("videos"):
    os.makedirs("videos")

# Create a Pyrogram client instance
app = Client(
    "shorts_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Call the function to set up our handlers
setup_handlers(app)

if __name__ == '__main__':
    print("Starting bot...")
    app.run()

