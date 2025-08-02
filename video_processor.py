import subprocess
import shlex
import os
import json

def get_video_metadata(video_path):
    """Get video duration and other metadata using ffprobe."""
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "json",
            video_path
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        metadata = json.loads(result.stdout)
        duration = float(metadata['format']['duration'])
        return duration
    except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error getting video metadata: {e}")
        return None

def generate_clips(video_path, duration=30, ratio="9:16", clip_count=5, watermark_pos="top-right"):
    """
    Generates multiple video clips with specified duration, aspect ratio, and watermark.
    
    Args:
        video_path (str): The path to the input video.
        duration (int): The duration of each output clip in seconds.
        ratio (str): The aspect ratio, e.g., "9:16", "1:1".
        clip_count (int): The number of clips to generate.
        watermark_pos (str): The position of the watermark ("tl", "tr", "bl", "br").
    
    Returns:
        list: A list of paths to the generated clip files.
    """
    clips = []
    total_duration = get_video_metadata(video_path)
    if total_duration is None:
        return []
    
    # Create a directory for generated clips
    output_dir = "generated_clips"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Calculate crop filter based on aspect ratio
    if ratio == "9:16":
        crop_filter = "crop=ih*9/16:ih"
    elif ratio == "4:3":
        crop_filter = "crop=ih*4/3:ih"
    elif ratio == "1:1":
        crop_filter = "crop=ih:ih"
    elif ratio == "16:9":
        crop_filter = "crop=iw:ih" # No crop needed for 16:9
    else: # "original"
        crop_filter = "scale=w=1080:h=1920:force_original_aspect_ratio=increase" # Example, you can adjust
    
    # Calculate watermark position
    watermark_text = "Your Watermark"
    watermark_x, watermark_y = "10", "10"
    if watermark_pos == "tr":
        watermark_x = "w-tw-10"
        watermark_y = "10"
    elif watermark_pos == "bl":
        watermark_x = "10"
        watermark_y = "h-th-10"
    elif watermark_pos == "br":
        watermark_x = "w-tw-10"
        watermark_y = "h-th-10"
    
    # Determine the number of intervals to create clips
    interval = (total_duration - duration) // clip_count if total_duration > duration else 0
    
    for i in range(clip_count):
        start_time = i * interval
        output_file = os.path.join(output_dir, f"clip_{i}.mp4")
        
        ffmpeg_cmd = [
            "ffmpeg",
            "-ss", str(start_time),
            "-i", video_path,
            "-t", str(duration),
            "-vf", f"{crop_filter},drawtext=text='{watermark_text}':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:x={watermark_x}:y={watermark_y}:fontsize=50:fontcolor=white@0.8",
            "-c:a", "copy",
            output_file,
            "-y" # Overwrite output files without asking
        ]
        
        try:
            # We use shlex.split for safety, but with -y it's better to pass a list
            # We also need a font file, which you'll need to make sure is available in the Docker image
            print(f"Running FFmpeg command: {' '.join(ffmpeg_cmd)}")
            subprocess.run(ffmpeg_cmd, check=True)
            clips.append(output_file)
        except subprocess.CalledProcessError as e:
            print(f"Error processing video with FFmpeg: {e}")
            
    return clips

