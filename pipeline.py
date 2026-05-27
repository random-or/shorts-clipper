import re
import subprocess
import sys
import tempfile
import traceback
from datetime import datetime
from pathlib import Path

from analyzer import find_best_segment
from editor import download_video, process_video
from scout import get_trending_link
from shorts_clipper.core.models import TranscriptSegment
from shorts_clipper.core.settings import Settings
from subtitles import generate_subtitles, get_local_transcription


def srt_time_to_seconds(time_str):
    """Converts HH:MM:SS,mmm to float seconds."""
    h, m, s_ms = time_str.split(':')
    s, ms = s_ms.split(',')
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000

def get_youtube_subtitles(url, work_path):
    """Downloads English auto-generated or manual subtitles from YouTube and parses them."""
    print("\n--- 1. FETCHING NATIVE ENGLISH SUBTITLES ---")
    output_base = work_path / "subs"
    command = [
        "yt-dlp",
        "--write-auto-subs",
        "--write-subs",
        "--sub-lang", "en,en-orig",
        "--sub-format", "srt",
        "--skip-download",
        "-o", str(output_base),
        url
    ]
    try:
        subprocess.run(command, check=True, capture_output=True)
    except subprocess.CalledProcessError:
        print("⚠️ No English auto-subtitles found. Pipeline cannot proceed safely.")
        return []
    
    # Find any .en.srt or .en-orig.srt file
    subs_files = list(work_path.glob("subs.en*.srt"))
    if not subs_files:
        return []
    
    srt_path = subs_files[0]
    with open(srt_path, encoding='utf-8') as f:
        content = f.read()
    
    # Basic SRT parser
    blocks = re.split(r'\n\s*\n', content.strip())
    segments = []
    for block in blocks:
        lines = block.split('\n')
        if len(lines) >= 3:
            times = re.findall(r'(\d+:\d+:\d+,\d+)', lines[1])
            if len(times) == 2:
                start = srt_time_to_seconds(times[0])
                end = srt_time_to_seconds(times[1])
                text = " ".join(lines[2:]).strip()
                segments.append(TranscriptSegment(start=start, end=end, text=text))
    
    print(f"✅ Loaded {len(segments)} English subtitle segments.")
    return segments

def run_pipeline(url, settings: Settings | None = None):
    if settings is None:
        settings = Settings.from_env()

    print(f"🚀 STARTING AUTONOMOUS ENGLISH FACTORY FOR: {url}")

    # Ensure output directory exists
    output_dir = settings.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="shorts_clipper_") as work_dir:
        work_path = Path(work_dir)
        
        try:
            # 1. Fetch transcript
            segments = get_youtube_subtitles(url, work_path)
            
            micro_clip_path = work_path / "micro_clip.mp4"
            
            if not segments:
                print("⚠️ No English auto-subtitles found. Engaging Local Whisper Fallback.")
                # If no transcript, we pick a default 30s window (e.g., 10s to 40s)
                start_time, end_time = 10.0, 40.0
                visual_layout = "crop_center"
                download_video(url, str(micro_clip_path), start_time=start_time, end_time=end_time)
                
                # Transcribe ONLY the 30s micro-clip locally
                segments = get_local_transcription(str(micro_clip_path))
            else:
                transcript_text = "\n".join(
                    f"[{seg.start:.1f}s - {seg.end:.1f}s] {seg.text}"
                    for seg in segments
                )

                # 2. Analyze with Gemini
                analysis_result = find_best_segment(transcript_text)
                try:
                    parts = analysis_result.split(',')
                    start_time, end_time = float(parts[0]), float(parts[1])
                    visual_layout = parts[2] if len(parts) > 2 else "crop_center"
                except (ValueError, IndexError):
                    print(f"❌ ERROR: Gemini returned invalid format: {analysis_result}")
                    return

                # 3. Download micro-clip using yt-dlp sections
                download_video(url, str(micro_clip_path), start_time=start_time, end_time=end_time)
            
            # 4. Vertical Crop (No subclipping here as it's already pre-snipped)
            print("\n--- 4. PROCESSING VERTICAL CROP ---")
            cropped_clip_path = work_path / "cropped.mp4"
            process_video(
                str(micro_clip_path), start_time, end_time,
                str(cropped_clip_path), visual_layout,
            )
            
            # 5. Burn Subtitles and Finalize
            print("\n--- 5. ASSEMBLING FINAL MOVIEPY COMPILATION ---")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            final_output = output_dir / f"clip_{timestamp}.mp4"
            generate_subtitles(
                str(cropped_clip_path),
                segments,
                start_time,
                end_time,
                str(final_output)
            )
            
            print("\n✅ SUCCESS! Autonomous English Factory is LIVE.")
            print(f"🔥 Viral clip ready at: {final_output}")
            
        except Exception as e:
            print(f"❌ PIPELINE FAILED: {e}")
            traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        # No link provided? Autopilot engaged.
        video_url = get_trending_link()
    else:
        # Manual override for specific target sniping.
        video_url = sys.argv[1]
    
    run_pipeline(video_url)
