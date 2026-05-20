import os
from moviepy import VideoFileClip, TextClip, CompositeVideoClip, ColorClip

def generate_subtitles(video_path, segments, start_time, end_time, output_path="final_video.mp4"):
    """
    Parses word-level timestamps and burns them into the video.
    """
    print(f"--- Generating subtitles for: {video_path} ---")
    
    video = VideoFileClip(video_path)
    w, h = video.size
    
    subtitle_clips = []
    
    for segment in segments:
        if segment.words:
            for word_info in segment.words:
                word = word_info.word.strip().upper()
                w_start = word_info.start
                w_end = word_info.end
                
                # Check if the word is within our selected window
                if w_start >= start_time and w_end <= end_time:
                    # Adjust timing to be relative to the start of the clip
                    rel_start = w_start - start_time
                    rel_end = w_end - start_time
                    duration = rel_end - rel_start
                    
                    if duration <= 0:
                        continue
                        
                    # Create a stylish text clip
                    # Note: moviepy v2.x TextClip parameters might differ slightly
                    # Using common parameters for a "Shorts" look
                    try:
                        txt = TextClip(
                            text=word,
                            font_size=100,
                            color='yellow',
                            font='DejaVuSans-Bold', # Basic font usually available on Linux
                            stroke_color='black',
                            stroke_width=2,
                            method='label'
                        ).with_start(rel_start).with_duration(duration).with_position(('center', h * 0.7))
                        
                        subtitle_clips.append(txt)
                    except Exception as e:
                        print(f"Error creating TextClip for word '{word}': {e}")
                        continue

    if not subtitle_clips:
        print("No subtitles found in this time range.")
        video.write_videofile(output_path, codec="libx264", audio_codec="aac")
        return output_path

    # Composite the subtitles over the video
    result = CompositeVideoClip([video] + subtitle_clips)
    
    print(f"--- Exporting final video with subtitles to {output_path} ---")
    result.write_videofile(output_path, codec="libx264", audio_codec="aac")
    
    video.close()
    result.close()
    
    return output_path

if __name__ == "__main__":
    print("This script is intended to be called from pipeline.py")
