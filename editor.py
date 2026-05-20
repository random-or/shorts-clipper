import os
import sys
import subprocess
try:
    from moviepy import VideoFileClip
except ImportError:
    print("Error: moviepy not found. Please install it using 'pip install moviepy'.")
    sys.exit(1)

def download_video(url, output_path="raw_video.mp4"):
    """
    Downloads the full video from the given URL using yt-dlp.
    """
    print(f"--- Downloading video: {url} ---")
    command = [
        "yt-dlp",
        "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "-o", output_path,
        url
    ]
    subprocess.run(command, check=True)
    return output_path

def process_video(input_path, start_time, end_time, output_path="output_short.mp4"):
    """
    Slices the video from start_time to end_time and crops it to a 9:16 vertical layout.
    """
    print(f"--- Processing video: {start_time}s to {end_time}s ---")
    
    # 1. Load the video and slice it
    clip = VideoFileClip(input_path).subclipped(start_time, end_time)
    
    # 2. Calculate the crop for 9:16 vertical layout
    # Original dimensions
    w, h = clip.size
    
    # Target Aspect Ratio (9:16)
    target_ratio = 9 / 16
    
    # Math Explanation:
    # We want to maintain the 9:16 ratio.
    # If the video is wider than 9:16 (most common), we crop the sides.
    # If the video is taller than 9:16, we crop the top/bottom.
    
    if (w / h) > target_ratio:
        # Case: Video is too wide (e.g., 16:9)
        # We keep the full height (h) and calculate the new width (new_w)
        # new_w / h = 9 / 16  =>  new_w = h * (9 / 16)
        new_w = h * target_ratio
        
        # To center the crop, we find the difference in width and split it
        # x_start = (original_width - target_width) / 2
        x1 = (w - new_w) / 2
        x2 = x1 + new_w
        y1, y2 = 0, h
        print(f"Cropping width: {w} -> {new_w} (centered)")
    else:
        # Case: Video is too tall (rare for standard landscape)
        # We keep the full width (w) and calculate the new height (new_h)
        # w / new_h = 9 / 16  =>  new_h = w / (9 / 16)
        new_h = w / target_ratio
        
        # To center the crop, we find the difference in height and split it
        # y_start = (original_height - target_height) / 2
        y1 = (h - new_h) / 2
        y2 = y1 + new_h
        x1, x2 = 0, w
        print(f"Cropping height: {h} -> {new_h} (centered)")

    # Perform the crop
    cropped_clip = clip.cropped(x1=x1, y1=y1, x2=x2, y2=y2)
    
    # 3. Resize to final dimensions (1080 x 1920)
    # moviepy maintains aspect ratio during resize if only one dimension is provided.
    final_clip = cropped_clip.resized(height=1920)
    
    # 4. Write the output file
    print(f"--- Exporting to {output_path} ---")
    final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac")
    
    # Close clips to free resources
    clip.close()
    final_clip.close()
    
    return output_path

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python editor.py <url> <start_time> <end_time>")
        sys.exit(1)
        
    url = sys.argv[1]
    start = float(sys.argv[2])
    end = float(sys.argv[3])
    
    raw_video = download_video(url)
    process_video(raw_video, start, end)
