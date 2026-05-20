import os
import sys
import shutil
from transcribe import download_audio, transcribe_audio
from analyzer import find_best_segment
from editor import download_video, process_video
from subtitles import generate_subtitles

def run_pipeline(url):
    print(f"🚀 STARTING PIPELINE FOR: {url}")
    
    # Files to cleanup later
    temp_files = []
    
    try:
        # 1. Download and Transcribe
        audio_path = download_audio(url)
        temp_files.append(audio_path)
        
        segments = transcribe_audio(audio_path)
        
        # 2. Prepare transcript for Gemini
        transcript_text = ""
        for segment in segments:
            transcript_text += f"[{segment.start:.2f}s -> {segment.end:.2f}s]: {segment.text}\n"
            
        # 3. Analyze with Gemini
        # Ensure API key is present
        if not os.environ.get("GEMINI_API_KEY"):
            print("ERROR: GEMINI_API_KEY not found in environment.")
            return

        time_range = find_best_segment(transcript_text)
        try:
            start_time, end_time = map(float, time_range.split(','))
        except ValueError:
            print(f"ERROR: Gemini returned invalid format: {time_range}")
            return
            
        # 4. Download and Edit Video
        raw_video_path = "raw_video.mp4"
        download_video(url, raw_video_path)
        temp_files.append(raw_video_path)
        
        cropped_video_path = "output_short.mp4"
        process_video(raw_video_path, start_time, end_time, cropped_video_path)
        temp_files.append(cropped_video_path)
        
        # 5. Add Subtitles
        final_video_path = "final_output.mp4"
        generate_subtitles(cropped_video_path, segments, start_time, end_time, final_video_path)
        
        print(f"\n✅ SUCCESS! Your video is ready at: {final_video_path}")
        
    except Exception as e:
        print(f"❌ PIPELINE FAILED: {e}")
    finally:
        # 6. Cleanup
        print("\n--- Cleaning up temporary files ---")
        for f in temp_files:
            if os.path.exists(f):
                os.remove(f)
                print(f"Removed: {f}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python pipeline.py <youtube_url>")
    else:
        video_url = sys.argv[1]
        run_pipeline(video_url)
