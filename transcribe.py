import os
from yt_dlp import YoutubeDL
from faster_whisper import WhisperModel

def download_audio(youtube_url, output_path="temp_audio.mp3"):
    print("--- 1. DOWNLOADING AUDIO STREAM ---")
    
    # Base name without extension for outtmpl
    base_name = os.path.splitext(output_path)[0]

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f'{base_name}.%(ext)s',
        'retries': 10,
        'fragment_retries': 10,
        'file_access_retries': 5,
        'retry_sleep_functions': {'http': lambda n: 5}, # Sleep 5s between retries
        'nopart': True, # Don't use .part files, download directly
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }
    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([youtube_url])
    return output_path

def transcribe_audio(audio_file):
    print("\n--- 2. TRANSCRIBING AUDIO LOCALLY (FREE) ---")
    # Using the light 'tiny' model so it runs incredibly fast on regular CPUs
    model = WhisperModel("tiny.en", device="cpu", compute_type="int8", download_root="./models")
    
    # vad_filter=True skips silent parts, massively speeding up CPU processing
    segments, info = model.transcribe(audio_file, beam_size=5, word_timestamps=True, vad_filter=True)
    print(f"Detected language: '{info.language}' with probability {info.language_probability:.2f}")
    
    print("\n--- ⚡ REAL-TIME TRANSCRIPTION STREAM ---")
    processed_segments = []
    
    # By iterating directly over the generator, we stream the output to the console 
    # as soon as it's processed, instead of freezing while waiting for the whole video.
    for segment in segments:
        print(f"[{segment.start:.2f}s -> {segment.end:.2f}s]: {segment.text}")
        processed_segments.append(segment)
        
    return processed_segments

if __name__ == "__main__":
    # Feel free to change this URL to any short YouTube video you want to try!
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ" 
    
    audio_path = download_audio(test_url)
    transcribe_audio(audio_path)
    
    # Cleans up the temporary audio file so your machine stays uncluttered
    if os.path.exists(audio_path):
        os.remove(audio_path)

