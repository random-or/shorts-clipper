import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta

from shorts_clipper.core.settings import Settings

settings = Settings.from_env()
api_key = settings.youtube_api_key

cutoff = datetime.now(UTC) - timedelta(days=7)
after_str = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")

url = "https://www.googleapis.com/youtube/v3/search?"
params = {
    "part": "id",
    "type": "video",
    "q": "tech",
    "order": "viewCount",
    "publishedAfter": after_str,
    "videoDuration": "medium",
    "maxResults": "1",
    "key": api_key,
}
print("TESTING URL:", url + urllib.parse.urlencode(params).replace(api_key, "HIDDEN"))
try:
    with urllib.request.urlopen(url + urllib.parse.urlencode(params)) as resp:
        print("SUCCESS")
except Exception as e:
    import urllib.error

    if isinstance(e, urllib.error.HTTPError):
        print("ERROR BODY:", e.read().decode())
    else:
        print("ERROR:", e)
