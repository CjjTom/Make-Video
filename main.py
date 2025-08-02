# main.py
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import sys

from pyrogram import Client
from config import API_ID, API_HASH, BOT_TOKEN
from handlers import setup_handlers

# A simple HTTP server for Koyeb's health checks.
# It responds with a "200 OK" status, indicating the bot is alive.
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Bot is running")

def run_health_check_server():
    """
    Runs the health check server on port 8080.
    """
    server = HTTPServer(('0.0.0.0', 8080), HealthCheckHandler)
    print("Health check server started on port 8080.")
    server.serve_forever()

# Create a directory to store videos if it doesn't exist
if not os.path.exists("videos"):
    os.makedirs("videos")
    print("Created 'videos' directory.")

print("Attempting to initialize Pyrogram client...")
try:
    # Create a Pyrogram client instance
    app = Client(
        "shorts_bot",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN
    )
    print("Pyrogram client initialized successfully.")
    
    # Call the function to set up our handlers
    setup_handlers(app)
    print("Handlers set up.")
    
    # Start the health check server in a separate thread
    health_thread = threading.Thread(target=run_health_check_server, daemon=True)
    health_thread.start()

    print("Starting bot...")
    app.run()
    print("Bot has started running.")

except Exception as e:
    print(f"An error occurred during bot startup: {e}")
    # Exit with a non-zero status to signal a failure
    sys.exit(1)
