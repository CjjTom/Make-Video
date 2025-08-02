# Use a minimal Python 3.9 image as the base
FROM python:3.9-slim

# Set the working directory for the application
WORKDIR /app

# Install system dependencies, including FFmpeg for video processing
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the main application file into the container
COPY main.py .

# Expose port 8080 for the health check server
EXPOSE 8080

# The command to run the bot when the container starts
CMD ["python", "main.py"]
