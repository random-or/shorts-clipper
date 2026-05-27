import json
import subprocess
import sys


def get_trending_link():
    """
    Scouts for high-signal global English content suitable for clipping.
    Filters for long-form videos (>120s) with verified English subtitles.
    """
    print("\n🚀 SCOUTING THE GLOBAL ENGLISH RADAR: HUNTING FOR ALPHA...")
    
    search_query = (
        "ytsearch10:viral podcast clips english "
        "OR trending gaming clip OR mrbeast speed streams"
    )
    
    command = [
        'yt-dlp',
        search_query,
        '--flat-playlist',
        '--dump-single-json',
        '--retries', '10',
        '--quiet'
    ]
    
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        
        if 'entries' not in data:
            print("⚠️ SEARCH FAILED TO RETURN ENTRIES.")
            return None

        for entry in data['entries']:
            video_id = entry['id']
            url = f"https://www.youtube.com/watch?v={video_id}"
            
            # Get detailed info for filtering
            info_command = [
                'yt-dlp',
                '--dump-json',
                '--skip-download',
                url
            ]
            info_result = subprocess.run(info_command, capture_output=True, text=True, check=True)
            info = json.loads(info_result.stdout)
            
            duration = info.get('duration', 0)
            subtitles = info.get('subtitles', {})
            auto_subs = info.get('automatic_captions', {})
            
            # Filters: 
            # 1. Long-form (> 120s) - effectively excludes Shorts
            # 2. English subtitles (manual or auto)
            has_en = (
                "en" in subtitles or "en-orig" in subtitles
                or "en" in auto_subs or "en-orig" in auto_subs
            )
            
            if duration > 120 and has_en:
                print(f"🎯 GLOBAL ALPHA TARGET ACQUIRED: {url}")
                return url
            else:
                print(f"⏭️ Skipping {url} (Duration: {duration}s, EN Subs: {has_en})")

        print("⚠️ NO SUITABLE TARGETS FOUND IN TOP 10.")
        return None
            
    except Exception as e:
        print(f"❌ SCOUTING FAILED: {e}")
        return None

if __name__ == "__main__":
    link = get_trending_link()
    if link:
        print(link)
    else:
        sys.exit(1)
