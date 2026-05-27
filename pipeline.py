"""Root pipeline.py — thin wrapper for backward compatibility.

All logic has moved to shorts_clipper/pipeline/runner.py.
Use: python -m shorts_clipper clip <url>
  or: python -m shorts_clipper autopilot
"""

import sys

from shorts_clipper.core.logging import configure_logging
from shorts_clipper.core.settings import Settings
from shorts_clipper.pipeline.runner import run
from shorts_clipper.scout.trending import get_trending_link

if __name__ == "__main__":
    configure_logging("INFO")
    settings = Settings.from_env()

    if len(sys.argv) < 2:
        url = get_trending_link()
        if not url:
            print("❌ Scout found no suitable video.")
            sys.exit(1)
    else:
        url = sys.argv[1]

    try:
        out = run(url, settings=settings)
        print(f"\n🔥 Clip ready: {out}")
    except Exception as exc:
        print(f"❌ FAILED: {exc}")
        sys.exit(1)
