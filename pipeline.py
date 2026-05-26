import os
import sys
import tempfile
import subprocess
from pathlib import Path

from transcribe import download_audio, transcribe_audio
from analyzer import find_best_segment
from editor import download_video
from scout import get_trending_link
from shorts_clipper.transcription.formatting import format_transcript, to_srt
from shorts_clipper.utils.video import get_video_metadata
from shorts_clipper.rendering.ffmpeg import build_vertical_render_command, FfmpegRenderOptions

def run_pipeline(url):
    print(f"🚀 STARTING PRODUCTION PIPELINE FOR: {url}")
    
    # Use a unique work directory per job
    with tempfile.TemporaryDirectory(prefix="shorts_clipper_") as work_dir:
        work_path = Path(work_dir)
        print(f"📁 Work directory: {work_path}")
        
        try:
            # 1. Download and Transcribe
            audio_path = str(work_path / "temp_audio.mp3")
            download_audio(url, audio_path)
            segments = transcribe_audio(audio_path)
            
            # 2. Prepare transcript for Gemini
            transcript_text = format_transcript(segments)
            
            # 3. Analyze with Gemini / Fallback
            raw_video_path = work_path / "raw_video.mp4"
            
            # We need metadata to validate timestamps
            print(f"--- Downloading source video for metadata and rendering ---")
            download_video(url, str(raw_video_path))
            metadata = get_video_metadata(str(raw_video_path))
            print(f"Source video: {metadata.width}x{metadata.height}, {metadata.duration:.2f}s")

            if not segments:
                print("⚠️ NO SPEECH DETECTED. Using duration-based fallback.")
                start_time = 0.0
                end_time = min(metadata.duration, 30.0)
            else:
                time_range = find_best_segment(transcript_text)
                try:
                    start_time, end_time = map(float, time_range.split(','))
                except ValueError:
                    print(f"ERROR: Gemini returned invalid format: {time_range}")
                    return
                
                # Sanity check timestamps
                if start_time >= metadata.duration:
                    print(f"⚠️ Start time {start_time} exceeds duration {metadata.duration}. Resetting to 0.")
                    start_time = 0.0
                
                if end_time <= start_time:
                    print(f"⚠️ End time {end_time} is before start time {start_time}. Using 30s window.")
                    end_time = min(start_time + 30.0, metadata.duration)
                
                end_time = min(end_time, metadata.duration)

            # 4. Generate SRT if there are segments
            srt_path = None
            if segments:
                srt_path = work_path / "subtitles.srt"
                srt_content = to_srt(segments, start_offset=start_time)
                srt_path.write_text(srt_content)
            
            # 5. Single-Pass Render with Ffmpeg
            final_output = Path("final_output.mp4").absolute()
            render_opts = FfmpegRenderOptions(
                target_width=1080,
                target_height=1920,
                preset="fast",
                font_size=24
            )
            
            # We change to work_dir to make subtitle path relative for ffmpeg
            old_cwd = os.getcwd()
            os.chdir(work_dir)
            try:
                render_cmd = build_vertical_render_command(
                    input_path="raw_video.mp4",
                    output_path=final_output,
                    start=start_time,
                    end=end_time,
                    source_width=metadata.width,
                    source_height=metadata.height,
                    subtitles_path="subtitles.srt" if srt_path else None,
                    options=render_opts
                )
                
                print(f"\n--- 🎬 RENDERING SINGLE PASS: {start_time:.2f}s to {end_time:.2f}s ---")
                print(f"Command: {' '.join(render_cmd)}")
                subprocess.run(render_cmd, check=True)
            finally:
                os.chdir(old_cwd)
            
            print(f"\n✅ SUCCESS! Sexy video ready at: {final_output}")
            
        except Exception as e:
            print(f"❌ PIPELINE FAILED: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        # No link provided? Autopilot engaged.
        video_url = get_trending_link()
    else:
        # Manual override for specific target sniping.
        video_url = sys.argv[1]
    
    run_pipeline(video_url)
