import math
import random
from datetime import UTC, datetime, timedelta

from shorts_clipper.core.settings import Settings
from shorts_clipper.scout.youtube_api import YouTubeAPIClient

settings = Settings.from_env()
api_key = settings.youtube_api_key
client = YouTubeAPIClient(api_key)


def model_A(video, hours_live):
    views = max(video.get("view_count", 0), 1)
    likes = video.get("like_count", 0)
    comments = video.get("comment_count", 0)

    velocity_raw = views / hours_live
    velocity_score = min(10.0, math.log1p(velocity_raw) / math.log1p(10_000) * 10)

    engagement_ratio = (likes + comments * 2) / views if views > 0 else 0
    engagement_score = min(10.0, engagement_ratio * 100)

    recency_score = 10.0 * math.exp(-hours_live / 24.0 * math.log(2))
    channel_momentum = min(10.0, math.log1p(likes) / math.log1p(1000) * 10)

    score = (
        velocity_score * 0.40
        + engagement_score * 0.30
        + recency_score * 0.20
        + channel_momentum * 0.10
    )
    return score


def model_B(video, hours_live):
    views = max(video.get("view_count", 0), 1)
    likes = video.get("like_count", 0)
    comments = video.get("comment_count", 0)

    views_velocity = views / hours_live
    velocity_score = views_velocity / 1000

    engagement_ratio = (likes + (comments * 2)) / views if views > 0 else 0
    engagement_score = min(20.0, engagement_ratio * 200)

    recency_bonus = 15.0 if hours_live < 24 else (5.0 if hours_live < 72 else 0.0)
    momentum_score = math.log1p(likes) / math.log1p(10_000) * 5

    score = velocity_score + engagement_score + recency_bonus + momentum_score
    return score


queries = [
    "tech",
    "finance",
    "gaming",
    "news",
    "sports",
    "podcast",
    "comedy",
    "motivation",
    "vlog",
    "fitness",
]
cutoff = datetime.now(UTC) - timedelta(days=7)

all_candidates = []

print("Fetching API data for 10 niches to build a pool of candidates...")
for q in queries:
    try:
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
                    "channel_title": snippet.get("channelTitle", ""),
                    "view_count": int(stats.get("viewCount", 0)),
                    "like_count": int(stats.get("likeCount", 0)),
                    "comment_count": int(stats.get("commentCount", 0)),
                }

                pub_str = v["published_at"]
                if pub_str:
                    published = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
                    hours_live = max((datetime.now(UTC) - published).total_seconds() / 3600, 1)

                    if v["view_count"] > 1000 and hours_live > 1:
                        v["hours_live"] = hours_live
                        v["vph"] = v["view_count"] / hours_live
                        v["eng_ratio"] = (v["like_count"] + v["comment_count"]) / v["view_count"]
                        v["score_A"] = model_A(v, hours_live)
                        v["score_B"] = model_B(v, hours_live)
                        all_candidates.append(v)
    except Exception as e:
        print(f"Failed query {q}: {e}")

print(f"Total candidates gathered: {len(all_candidates)}")

# Simulate 50 scout runs by taking random slices of 15 candidates
runs = 50
winners_A = []
winners_B = []
overlap_count = 0

print("\n--- SIMULATING 50 SCOUT RUNS ---")
random.seed(42)

for i in range(runs):
    # random pool of 15 candidates
    pool = random.sample(all_candidates, min(15, len(all_candidates)))
    if not pool:
        break

    winner_A = max(pool, key=lambda x: x["score_A"])
    winner_B = max(pool, key=lambda x: x["score_B"])

    winners_A.append(winner_A)
    winners_B.append(winner_B)

    if winner_A["id"] == winner_B["id"]:
        overlap_count += 1

    if i < 5:  # Print first 5 for inspection
        print(f"\nRun {i + 1}:")
        print(
            f"  Model A Winner: {winner_A['title'][:40]:<42} | Views: {winner_A['view_count']:<8} | Age: {round(winner_A['hours_live'], 1):<5} | VPH: {round(winner_A['vph'], 1):<8} | Score: {round(winner_A['score_A'], 2)}"
        )
        print(
            f"  Model B Winner: {winner_B['title'][:40]:<42} | Views: {winner_B['view_count']:<8} | Age: {round(winner_B['hours_live'], 1):<5} | VPH: {round(winner_B['vph'], 1):<8} | Score: {round(winner_B['score_B'], 2)}"
        )

print("\n--- AGGREGATE METRICS ---")
print(f"Winner Overlap: {overlap_count / runs * 100:.1f}%")

avg_vel_A = sum(x["vph"] for x in winners_A) / runs
avg_vel_B = sum(x["vph"] for x in winners_B) / runs
print(f"Average Velocity of Winners -> Model A: {avg_vel_A:.1f} v/h | Model B: {avg_vel_B:.1f} v/h")

avg_views_A = sum(x["view_count"] for x in winners_A) / runs
avg_views_B = sum(x["view_count"] for x in winners_B) / runs
print(f"Average Views of Winners    -> Model A: {avg_views_A:.1f} | Model B: {avg_views_B:.1f}")

avg_age_A = sum(x["hours_live"] for x in winners_A) / runs
avg_age_B = sum(x["hours_live"] for x in winners_B) / runs
print(f"Average Age of Winners      -> Model A: {avg_age_A:.1f}h | Model B: {avg_age_B:.1f}h")

print("\n--- CASE ANALYSIS ---")
slower_A_count = 0
better_velocity_B = 0
large_channel_bias = 0

for i in range(runs):
    wa = winners_A[i]
    wb = winners_B[i]
    if wa["id"] != wb["id"]:
        if wa["vph"] < wb["vph"]:
            better_velocity_B += 1
            if wa["hours_live"] < wb["hours_live"]:
                slower_A_count += 1

        # Check if Model B winner is just an old massive video (e.g. huge views, low velocity relative to recent hits, or super old)
        if wb["hours_live"] > 100 and wb["view_count"] > 1_000_000 and wb["vph"] < 20000:
            large_channel_bias += 1

print(f"Cases where Model A selected a slower but newer video: {slower_A_count}")
print(f"Cases where Model B successfully selected a higher-velocity video: {better_velocity_B}")
print(
    f"Cases where Model B selected a stale large-channel video (Age>100h, Velocity<20k): {large_channel_bias}"
)

if better_velocity_B > 0 and large_channel_bias == 0:
    print("\nRECOMMENDATION: ADOPT ACCELERATION MODEL")
elif large_channel_bias > 5:
    print("\nRECOMMENDATION: HYBRID MODEL (Velocity needs capping or decay)")
else:
    print("\nRECOMMENDATION: KEEP CURRENT")
