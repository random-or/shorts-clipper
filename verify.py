import logging
import sys

from shorts_clipper.scout.trending import get_trending_link

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

print("Test: Search by channel (UCahJ9IsvXnaQiuNyWQSkrkw)")
get_trending_link(channel="UCahJ9IsvXnaQiuNyWQSkrkw", max_age_days=7)

print("\nTest: Search by niche (tech, strict 7 days)")
get_trending_link(niche="tech", max_age_days=7)
