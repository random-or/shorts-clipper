import subprocess
import json
import sys

def get_trending_link():
    """
    Scouts the #1 trending video on YouTube to ensure we are always clipping
    content that the algorithm is already pushing.
    """
    print("\n🚀 SCOUTING THE ALGO: HUNTING FOR TRENDING ALPHA...")
    
    command = [
        'yt-dlp',
        'ytsearch1:trending',
        '--flat-playlist',
        '--dump-single-json',
        '--retries', '10',
        '--fragment-retries', '10',
        '--file-access-retries', '5',
        '--quiet'
    ]
    
    backup_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ" # Rickroll is the ultimate viral fallback
    
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        
        # Parse the video ID from the search results
        if 'entries' in data and len(data['entries']) > 0:
            video_id = data['entries'][0]['id']
            url = f"https://www.youtube.com/watch?v={video_id}"
            print(f"🎯 TARGET ACQUIRED: {url}")
            return url
        else:
            print("⚠️ TRENDING FEED EMPTY. FALLING BACK TO LEGACY TRACK.")
            return backup_url
            
    except Exception as e:
        print(f"❌ SCOUTING FAILED: {e}")
        print(f"🔄 USING BACKUP VIRAL TRACK: {backup_url}")
        return backup_url

if __name__ == "__main__":
    # Test the scout
    print(get_trending_link())
