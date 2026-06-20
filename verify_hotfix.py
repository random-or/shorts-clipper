import logging
import os
import sqlite3
import sys
from pathlib import Path

from shorts_clipper.scout.trending import get_trending_link

# Load .env manually
env_path = Path(".env")
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()

# Clear cache entries for clean run
db_path = Path("outputs/jobs.db")
if db_path.exists():
    try:
        con = sqlite3.connect(db_path, check_same_thread=False)
        con.execute("DELETE FROM metadata_cache")
        con.commit()
        con.close()
    except Exception:
        pass

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)

print("--- RUNNING SCOUT V2 PRODUCTION HOTFIX VERIFICATION ---")
url = get_trending_link(niche="football fifa world cup 2026", keyword="football", max_age_days=7)
print(f"RESULT: {url}")
