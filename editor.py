import os
import sys
import subprocess
try:
    from moviepy import VideoFileClip, CompositeVideoClip
    import moviepy.video.fx as vfx
except ImportError:
    print("Error: moviepy not found. Please install it using 'pip install moviepy'.")
    sys.exit(1)

def download_video(url, output_path="raw_video.mp4", start_time=None, end_time=None):
    """
    Downloads the video (or a specific section) from the given URL using yt-dlp.
    """
    if start_time is not None and end_time is not None:
        print(f"--- Downloading video section: {url} ({start_time}s to {end_time}s) ---")
    else:
        print(f"--- Downloading full video: {url} ---")
    
    # Clean up any leftover partial files
    partial_path = f"{output_path}.part"
    if os.path.exists(partial_path):
        os.remove(partial_path)
    if os.path.exists(output_path):
        os.remove(output_path)

    command = [
        "yt-dlp",
        "--retries", "10",
        "--fragment-retries", "10",
        "--no-part",
        "-f", "bestvideo[ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--merge-output-format", "mp4",
        "-o", output_path,
    ]
    
    if start_time is not None and end_time is not None:
        # yt-dlp section syntax: *start-end
        command.extend(["--download-sections", f"*{start_time}-{end_time}"])
        
    command.append(url)
    
    subprocess.run(command, check=True)
    return output_path

def process_video(input_path, start_time, end_time, output_path="output_short.mp4", visual_layout="crop_center"):
    """
    Crops the video to a 9:16 vertical layout dynamically based on visual_layout.
    """
    print(f"--- Processing vertical layout: {start_time}s to {end_time}s (Layout: {visual_layout}) ---")
    
    # 1. Load the video
    clip = VideoFileClip(input_path)
    w, h = clip.size
    
    # Target dimensions (Instagram/TikTok standard 1080x1920)
    target_w, target_h = 1080, 1920
    
    bg_scale = max(target_w / w, target_h / h)
    clip_resized = clip.resized(bg_scale)
    bg_w, bg_h = clip_resized.size
    
    if visual_layout == "crop_left":
        x1 = 0
        y1 = (bg_h - 1920) / 2
        x2 = 1080
        y2 = y1 + 1920
        final_clip = clip_resized.cropped(x1=x1, y1=y1, x2=x2, y2=y2)
    elif visual_layout == "crop_right":
        x1 = bg_w - 1080
        y1 = (bg_h - 1920) / 2
        x2 = bg_w
        y2 = y1 + 1920
        final_clip = clip_resized.cropped(x1=x1, y1=y1, x2=x2, y2=y2)
    elif visual_layout == "split_screen":
        top = clip_resized.cropped(
            x1=(bg_w - 1080) / 2, y1=0,
            x2=(bg_w + 1080) / 2, y2=960
        ).with_position(("center", "top"))
        bottom = clip_resized.cropped(
            x1=(bg_w - 1080) / 2, y1=bg_h - 960,
            x2=(bg_w + 1080) / 2, y2=bg_h
        ).with_position(("center", "bottom"))
        final_clip = CompositeVideoClip([top, bottom], size=(1080, 1920))
    else:  # crop_center
        x1 = (bg_w - 1080) / 2
        y1 = (bg_h - 1920) / 2
        x2 = x1 + 1080
        y2 = y1 + 1920
        final_clip = clip_resized.cropped(x1=x1, y1=y1, x2=x2, y2=y2)
    
    # 5. Write the output file
    print(f"--- Exporting to {output_path} ---")
    final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=24)
    
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
