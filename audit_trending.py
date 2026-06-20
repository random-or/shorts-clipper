import logging
import math
from datetime import UTC, datetime, timedelta

from shorts_clipper.core.settings import Settings
from shorts_clipper.scout.youtube_api import YouTubeAPIClient

logging.basicConfig(level=logging.WARNING)

settings = Settings.from_env()
api_key = settings.youtube_api_key
client = YouTubeAPIClient(api_key)

queries = ["tech", "finance", "gaming", "news"]
cutoff = datetime.now(UTC) - timedelta(days=7)

print("AUDIT: Trending Quality Analysis\n")

all_videos = []

for q in queries:
    print(f"Fetching API data for query: {q}")
    ids = client.search(q, published_after=cutoff)
    if ids:
        details = client.get_video_details(ids)
        for item in details:
            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})
            v = {
                "id": item["id"],
                "title": snippet.get("title", ""),
                "published_at": snippet.get("publishedAt", ""),
                "view_count": int(stats.get("viewCount", 0)),
                "like_count": int(stats.get("likeCount", 0)),
                "comment_count": int(stats.get("commentCount", 0)),
            }

            pub_str = v["published_at"]
            if pub_str:
                published = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
                hours_live = max((datetime.now(UTC) - published).total_seconds() / 3600, 1)

                v["hours_live"] = round(hours_live, 1)
                v["views_per_hour"] = round(v["view_count"] / hours_live, 1)
                v["engagement_ratio"] = round(
                    (v["like_count"] + v["comment_count"]) / max(v["view_count"], 1) * 100, 2
                )

                # CURRENT SCORE LOGIC
                velocity_score = min(
                    10.0, math.log1p(v["views_per_hour"]) / math.log1p(10_000) * 10
                )
                engagement_score = min(10.0, v["engagement_ratio"] * 2)
                recency_score = 10.0 * math.exp(-hours_live / 24.0 * math.log(2))
                channel_momentum = min(10.0, math.log1p(v["like_count"]) / math.log1p(1000) * 10)

                v["current_score"] = round(
                    velocity_score * 0.40
                    + engagement_score * 0.30
                    + recency_score * 0.20
                    + channel_momentum * 0.10,
                    3,
                )

                all_videos.append(v)

# Sort by current score
all_videos.sort(key=lambda x: x["current_score"], reverse=True)

print(f"\nTotal Candidates Evaluated: {len(all_videos)}\n")

print("========== CURRENT ALGORITHM TOP 10 ==========")
print(f"{'Rank':<5} | {'Views':<10} | {'V/Hour':<10} | {'Age(h)':<7} | {'Score':<6} | Title")
for idx, v in enumerate(all_videos[:10], 1):
    print(
        f"{idx:<5} | {v['view_count']:<10} | {v['views_per_hour']:<10} | {v['hours_live']:<7} | {v['current_score']:<6} | {v['title'][:40]}"
    )

# Sort strictly by velocity
all_videos.sort(key=lambda x: x["views_per_hour"], reverse=True)

print("\n========== PURE VELOCITY TOP 10 ==========")
print(f"{'Rank':<5} | {'Views':<10} | {'V/Hour':<10} | {'Age(h)':<7} | {'Score':<6} | Title")
for idx, v in enumerate(all_videos[:10], 1):
    print(
        f"{idx:<5} | {v['view_count']:<10} | {v['views_per_hour']:<10} | {v['hours_live']:<7} | {v['current_score']:<6} | {v['title'][:40]}"
    )

# Analysis for accelerating vs accumulating
print("\n========== WEAKNESS ANALYSIS ==========")
# Find high view but old videos beating fast growing new videos
current_winner = max(all_videos, key=lambda x: x["current_score"])
fastest_video = all_videos[0]

print(
    f"Current Winner: {current_winner['title'][:30]}... ({current_winner['view_count']} views, {current_winner['hours_live']}h old, {current_winner['views_per_hour']} v/hr)"
)
print(
    f"Fastest Growing: {fastest_video['title'][:30]}... ({fastest_video['view_count']} views, {fastest_video['hours_live']}h old, {fastest_video['views_per_hour']} v/hr)"
)

if current_winner["id"] != fastest_video["id"]:
    print("\n⚠️  WEAKNESS DETECTED: The fastest growing video did NOT win.")
    if current_winner["hours_live"] > fastest_video["hours_live"]:
        print("An older, accumulating video defeated a newer, accelerating video.")
