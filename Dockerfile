# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Install FFmpeg and other necessary libraries
# We use apt-get to install system-level packages
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Expose the port the bot will run on (if needed for webhooks)
# For Pyrogram, webhooks are not always used, but it's good practice
EXPOSE 8080

# Command to run the application
# We use gunicorn to run a web server if you're using webhooks,
# but for a long-running Pyrogram bot, we'll just run the main script
CMD ["python", "main.py"]
