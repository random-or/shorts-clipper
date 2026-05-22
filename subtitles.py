import os
from moviepy import VideoFileClip, TextClip, CompositeVideoClip

def generate_subtitles(video_path, segments, start_time, end_time, output_path="final_video.mp4"):
    """
    Groups word-level timestamps into phrases and burns them into the video.
    """
    print(f"--- Generating subtitles for: {video_path} ---")
    
    video = VideoFileClip(video_path)
    w, h = video.size
    
    # 1. Collect all words within the selected time window
    all_words = []
    for segment in segments:
        if segment.words:
            for word_info in segment.words:
                # Check if the word is within our selected window
                if word_info.start >= start_time and word_info.end <= end_time:
                    all_words.append(word_info)
    
    if not all_words:
        print("No subtitles found in this time range.")
        video.write_videofile(output_path, codec="libx264", audio_codec="aac")
        return output_path

    # 2. Group words into logical 2-3 word chunks or at punctuation
    groups = []
    temp_group = []
    for i, word_info in enumerate(all_words):
        temp_group.append(word_info)
        word_text = word_info.word.strip()
        
        # Break condition: 3 words reached OR punctuation pause OR end of list
        if (len(temp_group) >= 3 or 
            word_text.endswith(('.', '!', '?', ',')) or 
            i == len(all_words) - 1):
            groups.append(temp_group)
            temp_group = []

    # 3. Create TextClips for each group
    subtitle_clips = []
    for group in groups:
        phrase = " ".join([w.word.strip().upper() for w in group])
        
        # Timing relative to the start of the clip
        rel_start = group[0].start - start_time
        rel_end = group[-1].end - start_time
        duration = rel_end - rel_start
        
        if duration <= 0:
            # Fallback for very fast words
            duration = 0.2
            
        try:
            txt = TextClip(
                text=phrase,
                font_size=80,
                color='white',
                font='DejaVuSans-Bold',
                stroke_color='black',
                stroke_width=3,
                method='caption',
                size=(600, 200)
            ).with_start(rel_start).with_duration(duration).with_position(('center', h * 0.65))
            
            subtitle_clips.append(txt)
        except Exception as e:
            print(f"Error creating TextClip for phrase '{phrase}': {e}")
            continue

    # 4. Composite and Export
    result = CompositeVideoClip([video] + subtitle_clips)
    
    print(f"--- Exporting final video with subtitles to {output_path} ---")
    result.write_videofile(output_path, codec="libx264", audio_codec="aac")
    
    video.close()
    result.close()
    
    return output_path

if __name__ == "__main__":
    print("This script is intended to be called from pipeline.py")
