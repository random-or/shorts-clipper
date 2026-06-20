import math
import random


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


def generate_mock_candidates(num=500):
    candidates = []
    for i in range(num):
        # mix of old huge videos, new viral, new dud, mid mid
        type_ = random.choices(
            ["mega_old", "viral_new", "dud", "slow_burn"], weights=[10, 10, 60, 20]
        )[0]

        if type_ == "mega_old":
            hours = random.uniform(72, 168)
            views = random.randint(1_000_000, 10_000_000)
            likes = int(views * random.uniform(0.01, 0.05))
            comments = int(likes * random.uniform(0.05, 0.2))
        elif type_ == "viral_new":
            hours = random.uniform(2, 48)
            vph = random.randint(20_000, 150_000)
            views = int(vph * hours)
            likes = int(views * random.uniform(0.05, 0.15))
            comments = int(likes * random.uniform(0.1, 0.3))
        elif type_ == "slow_burn":
            hours = random.uniform(12, 168)
            vph = random.randint(1000, 5000)
            views = int(vph * hours)
            likes = int(views * random.uniform(0.02, 0.08))
            comments = int(likes * random.uniform(0.05, 0.2))
        else:  # dud
            hours = random.uniform(1, 168)
            vph = random.randint(10, 500)
            views = int(vph * hours)
            likes = int(views * random.uniform(0.01, 0.04))
            comments = int(likes * random.uniform(0.01, 0.1))

        v = {
            "id": f"vid_{i}",
            "title": f"Video {i} ({type_})",
            "view_count": views,
            "like_count": likes,
            "comment_count": comments,
            "hours_live": hours,
            "vph": views / hours,
        }
        v["score_A"] = model_A(v, hours)
        v["score_B"] = model_B(v, hours)
        candidates.append(v)
    return candidates


all_candidates = generate_mock_candidates()
print(f"Total candidates gathered: {len(all_candidates)}")

runs = 50
winners_A = []
winners_B = []
overlap_count = 0

print("\n--- SIMULATING 50 SCOUT RUNS ---")
random.seed(42)

for i in range(runs):
    pool = random.sample(all_candidates, 15)

    winner_A = max(pool, key=lambda x: x["score_A"])
    winner_B = max(pool, key=lambda x: x["score_B"])

    winners_A.append(winner_A)
    winners_B.append(winner_B)

    if winner_A["id"] == winner_B["id"]:
        overlap_count += 1

    if i < 5:
        print(f"\nRun {i + 1}:")
        print(
            f"  Model A: {winner_A['title']:<25} | Views: {winner_A['view_count']:<8} | Age: {round(winner_A['hours_live'], 1):<5} | VPH: {round(winner_A['vph'], 1):<8} | Score: {round(winner_A['score_A'], 2)}"
        )
        print(
            f"  Model B: {winner_B['title']:<25} | Views: {winner_B['view_count']:<8} | Age: {round(winner_B['hours_live'], 1):<5} | VPH: {round(winner_B['vph'], 1):<8} | Score: {round(winner_B['score_B'], 2)}"
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

        # Check if Model B winner is just an old massive video
        if wb["hours_live"] > 72 and wb["view_count"] > 1_000_000 and wb["vph"] < 20000:
            large_channel_bias += 1

print(f"Cases where Model A selected a slower but newer video: {slower_A_count}")
print(f"Cases where Model B successfully selected a higher-velocity video: {better_velocity_B}")
print(
    f"Cases where Model B selected a stale large-channel video (Age>72h, Velocity<20k): {large_channel_bias}"
)

if better_velocity_B > 0 and large_channel_bias == 0:
    print("\nRECOMMENDATION: ADOPT ACCELERATION MODEL")
elif large_channel_bias > 5:
    print("\nRECOMMENDATION: HYBRID MODEL (Velocity needs capping or decay)")
else:
    print("\nRECOMMENDATION: HYBRID MODEL")
