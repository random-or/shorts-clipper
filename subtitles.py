import os
from moviepy import VideoFileClip, TextClip, CompositeVideoClip
from faster_whisper import WhisperModel
from shorts_clipper.core.models import TranscriptSegment, TranscriptWord

def get_local_transcription(video_path):
    """
    Performs local transcription using a lightweight Whisper model.
    Optimized for short clips.
    """
    print(f"--- Running local Whisper transcription for: {video_path} ---")
    # Using 'tiny' for < 5s performance on CPU
    model = WhisperModel("tiny", device="cpu", compute_type="int8")
    
    segments_generator, info = model.transcribe(video_path, beam_size=5, word_timestamps=True)
    
    segments = []
    for s in segments_generator:
        words = []
        if s.words:
            for w in s.words:
                words.append(TranscriptWord(start=w.start, end=w.end, word=w.word.strip()))
        
        segments.append(TranscriptSegment(
            start=s.start,
            end=s.end,
            text=s.text.strip(),
            words=words
        ))
    
    print(f"✅ Local transcription complete. Found {len(segments)} segments.")
    return segments

def generate_subtitles(video_path, segments, start_time, end_time, output_path="final_video.mp4"):
    """
    Groups word-level timestamps into phrases and burns them into the video.
    Optimized for High-Retention Instagram Style.
    """
    print(f"--- Generating high-retention subtitles for: {video_path} ---")
    
    video = VideoFileClip(video_path)
    w, h = video.size
    
    # 1. Collect all segments within the selected time window
    # Note: If segments were generated locally, start_time might be 0
    relevant_segments = []
    for segment in segments:
        if segment.start >= start_time and segment.end <= end_time:
            relevant_segments.append(segment)
    
    if not relevant_segments:
        # If no relevant segments found, maybe the segments are relative to the clip (0-based)
        # Check if the first segment starts near 0 and we are looking at a non-zero start_time
        if segments and segments[0].start < start_time and segments[-1].end < end_time:
            print("Detected relative segments, adjusting search window...")
            for segment in segments:
                # If we are transcribing the 30s clip itself, segments will be 0-30
                # We assume they match the video_path provided
                relevant_segments.append(segment)
            # Reset start_time for relative math if we use these segments
            start_time = 0

    if not relevant_segments:
        print("No subtitles found in this time range.")
        video.write_videofile(output_path, codec="libx264", audio_codec="aac")
        return output_path

    # 2. Break segments into logical 2-3 word chunks for that punchy "viral" feel
    all_chunks = []
    for seg in relevant_segments:
        if seg.words:
            # If we have word-level data, use it for precise chunks
            words = seg.words
            for i in range(0, len(words), 2): # Group by 2 words
                chunk = words[i:i+2]
                chunk_text = " ".join([w.word for w in chunk]).upper()
                all_chunks.append({
                    'text': chunk_text,
                    'start': chunk[0].start,
                    'end': chunk[-1].end
                })
        else:
            # Fallback to splitting text if no word-level data
            words = seg.text.split()
            if not words: continue
            
            chunk_count = (len(words) + 1) // 2
            duration_per_chunk = (seg.end - seg.start) / chunk_count
            
            for i in range(0, len(words), 2):
                chunk_text = " ".join(words[i:i+2]).upper()
                idx = i // 2
                chunk_start = seg.start + (idx * duration_per_chunk)
                all_chunks.append({
                    'text': chunk_text,
                    'start': chunk_start,
                    'end': min(chunk_start + duration_per_chunk, seg.end)
                })

    # 3. Create TextClips for each chunk
    subtitle_clips = []
    for chunk in all_chunks:
        # Timing relative to the start of the micro-clip
        rel_start = max(0, chunk['start'] - start_time)
        rel_end = chunk['end'] - start_time
        duration = rel_end - rel_start
        
        if duration <= 0:
            duration = 0.5 # Minimum visibility
            
        try:
            # High-signal styling: Bold, Yellow, Black Outline, Centered
            txt = TextClip(
                text=chunk['text'],
                font_size=80,
                color='yellow', 
                font='DejaVuSans-Bold',
                stroke_color='black',
                stroke_width=3,
                method='caption',
                text_align='center',
                size=(w * 0.9, None)
            ).with_start(rel_start).with_duration(duration).with_position(('center', h * 0.65))
            
            subtitle_clips.append(txt)
        except Exception as e:
            print(f"Error creating TextClip for chunk '{chunk['text']}': {e}")
            continue

    # 4. Composite and Export
    result = CompositeVideoClip([video] + subtitle_clips)
    
    print(f"--- Exporting final viral video with subtitles to {output_path} ---")
    result.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=24)
    
    video.close()
    result.close()
    
    return output_path

if __name__ == "__main__":
    print("This script is intended to be called from pipeline.py")
