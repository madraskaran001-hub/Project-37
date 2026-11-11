
import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "drug_candidates.json"

FEED_URL = (
    "https://www.fda.gov/about-fda/contact-fda/"
    "stay-informed/rss-feeds"
)

def fetch_feed():
    request = urllib.request.Request(
        FEED_URL,
        headers={
            "User-Agent": "Project37/1.0"
        }
    )

    with urllib.request.urlopen(
        request, timeout=30
    ) as response:
        return response.read()

def main():
    print("Project37 Drug Discovery")
    print("------------------------")

    data = fetch_feed()
    root = ET.fromstring(data)

    candidates = []

    for item in root.findall(".//item"):
        title = item.findtext("title", "").strip()
        link = item.findtext("link", "").strip()
        published = item.findtext("pubDate", "").strip()

        keywords = [
            "drug",
            "approval",
            "therapy",
            "treatment",
            "biologic"
        ]

        if any(
            word in title.lower()
            for word in keywords
        ):
            candidates.append({
                "title": title,
                "source": "FDA",
                "url": link,
                "published": published,
                "review_status": "pending",
                "discovered_at": datetime.now(
                    timezone.utc
                ).isoformat()
            })

    OUTPUT.write_text(
        json.dumps(
            candidates,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    print("Candidates found:", len(candidates))
    print("Saved:", OUTPUT.name)

if __name__ == "__main__":
    main()
