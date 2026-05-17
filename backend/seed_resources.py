"""One-time script to seed Resource table via youtube_agent for all categories."""
import asyncio
import sys
import os

# Run from backend/ directory: python seed_resources.py
sys.path.insert(0, os.path.dirname(__file__))

from app.services.db.session import get_session_factory
from app.services.youtube_agent import run_youtube_crawl_agent, CATEGORIES

LIMIT_PER_CATEGORY = 30


async def seed_category(category: str) -> None:
    db = get_session_factory()()
    try:
        print(f"\n[{category}] Starting crawl...")
        async for raw in run_youtube_crawl_agent(category, LIMIT_PER_CATEGORY, db):
            line = raw.strip()
            if not line.startswith("data:"):
                continue
            import json
            try:
                payload = json.loads(line[5:].strip())
                event = payload.get("event", "")
                data = payload.get("data", {})
                if event == "error":
                    print(f"  ERROR: {data}")
                elif event == "keyword_generation" and isinstance(data, dict) and data.get("status") == "completed":
                    print(f"  Keywords: {data.get('keywords')}")
                elif event == "youtube_search" and isinstance(data, dict) and data.get("status") == "completed":
                    print(f"  Found {data.get('videos_found', 0)} videos")
                elif event == "content_moderation" and isinstance(data, dict) and data.get("status") == "completed":
                    print(f"  Approved {data.get('approved', 0)}, rejected {data.get('rejected', 0)}")
                elif event == "db_insertion" and isinstance(data, dict) and data.get("status") == "completed":
                    print(f"  Inserted {data.get('inserted', 0)} new rows")
                elif event == "done":
                    results = data.get("results", []) if isinstance(data, dict) else []
                    print(f"  Done — {len(results)} total items")
            except Exception:
                pass
    finally:
        db.close()


async def main() -> None:
    categories = sys.argv[1:] or CATEGORIES
    print(f"Seeding categories: {categories}")
    for cat in categories:
        await seed_category(cat)
    print("\nDone seeding all categories.")


if __name__ == "__main__":
    asyncio.run(main())
