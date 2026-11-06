
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES_FILE = ROOT / "sources.json"
UPDATES_FILE = ROOT / "updates.json"

HEADERS = {"User-Agent": "project37-medical-updates/1.0"}


def clean_text(value):
    value = re.sub(r"<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", unescape(value)).strip()


def format_date(value):
    if not value:
        return datetime.now(timezone.utc).strftime("%d %B %Y")
    try:
        try:
            date = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            date = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return date.strftime("%d %B %Y")
    except (TypeError, ValueError):
        return datetime.now(timezone.utc).strftime("%d %B %Y")


def fetch_feed(source):
    request = urllib.request.Request(
        source["feed_url"], headers=HEADERS
    )
    with urllib.request.urlopen(request, timeout=25) as response:
        xml_data = response.read()

    root = ET.fromstring(xml_data)
    entries = root.findall(".//item")

    if not entries:
        entries = root.findall(".//{*}entry")

    results = []

    for entry in entries[:20]:
        title = entry.findtext("title") or ""
        link = entry.findtext("link") or ""

        if not link:
            link_element = entry.find("{*}link")
            if link_element is not None:
                link = link_element.attrib.get("href", "")

        summary = (
            entry.findtext("description")
            or entry.findtext("{*}summary")
            or entry.findtext("{*}content")
            or ""
        )

        date = (
            entry.findtext("pubDate")
            or entry.findtext("{*}published")
            or entry.findtext("{*}updated")
            or ""
        )

        if not title.strip() or not link.strip():
            continue

        results.append({
            "category": source["category"],
            "title": clean_text(title),
            "summary": clean_text(summary)[:400],
            "date": format_date(date),
            "source": source["name"],
            "url": link.strip(),
            "relevance": "Pending assessment"
        })

    return results


def main():
    sources = json.loads(SOURCES_FILE.read_text(encoding="utf-8"))
    updates = json.loads(UPDATES_FILE.read_text(encoding="utf-8"))

    if not isinstance(updates, list):
        raise ValueError("updates.json must contain a JSON array")

    known_urls = {
        item.get("url") for item in updates if item.get("url")
    }

    added = 0

    for source in sources:
        if source.get("method") != "rss" or not source.get("feed_url"):
            continue

        try:
            entries = fetch_feed(source)
            for item in entries:
                if item["url"] not in known_urls:
                    updates.append(item)
                    known_urls.add(item["url"])
                    added += 1
            print(f"Checked: {source['name']}")
        except Exception as error:
            print(f"Could not fetch {source['name']}: {error}")

    updates = updates[-200:]

    UPDATES_FILE.write_text(
        json.dumps(updates, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )

    print(f"New updates added: {added}")


if __name__ == "__main__":
    main()
