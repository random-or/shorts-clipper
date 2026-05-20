import os
from yt_dlp import YoutubeDL
from faster_whisper import WhisperModel

def download_audio(youtube_url):
    print("--- 1. DOWNLOADING AUDIO STREAM ---")
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'temp_audio.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }
    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([youtube_url])
    return "temp_audio.mp3"

def transcribe_audio(audio_file):
    print("\n--- 2. TRANSCRIBING AUDIO LOCALLY (FREE) ---")
    # Using the light 'tiny' model so it runs incredibly fast on regular CPUs
    model = WhisperModel("tiny.en", device="cpu", compute_type="int8", download_root="./models")
    
    segments, info = model.transcribe(audio_file, beam_size=5, word_timestamps=True)
    print(f"Detected language: '{info.language}' with probability {info.language_probability:.2f}")
    
    segments = list(segments)  # Convert generator to list to use it later
    
    print("\n--- TRANSCRIPT WITH TIMESTAMPS ---")
    for segment in segments:
        print(f"[{segment.start:.2f}s -> {segment.end:.2f}s]: {segment.text}")
    
    return segments

if __name__ == "__main__":
    # Feel free to change this URL to any short YouTube video you want to try!
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ" 
    
    audio_path = download_audio(test_url)
    transcribe_audio(audio_path)
    
    # Cleans up the temporary audio file so your machine stays uncluttered
    if os.path.exists(audio_path):
        os.remove(audio_path)

