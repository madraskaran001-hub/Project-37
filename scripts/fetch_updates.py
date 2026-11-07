import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parent.parent
SOURCES_FILE = ROOT / "sources.json"
UPDATES_FILE = ROOT / "updates.json"

HEADERS = {"User-Agent": "project37-medical-updates/1.0"}


def clean_text(value):
    value = re.sub(r"<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", unescape(value)).strip()


def format_date(value):
    if not value:
        return "Date not listed"

    try:
        try:
            date = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            date = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return date.strftime("%d %B %Y")
    except (TypeError, ValueError):
        return value.strip()


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

        if title.strip() and link.strip():
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


class TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.row_text = []
        self.links = []
        self.anchor_text = []
        self.href = None
        self.in_row = False
        self.in_anchor = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)

        if tag == "tr":
            self.in_row = True
            self.row_text = []
            self.links = []

        elif tag == "a" and self.in_row:
            self.in_anchor = True
            self.href = attrs.get("href", "")
            self.anchor_text = []

    def handle_data(self, data):
        if self.in_row:
            self.row_text.append(data)

        if self.in_anchor:
            self.anchor_text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.in_anchor:
            self.links.append((
                self.href,
                clean_text(" ".join(self.anchor_text))
            ))
            self.in_anchor = False

        elif tag == "tr" and self.in_row:
            text = clean_text(" ".join(self.row_text))

            for href, anchor_text in self.links:
                if href:
                    self.rows.append((text, href, anchor_text))

            self.in_row = False


def extract_date(text):
    patterns = [
        r"\d{4}-[A-Za-z]{3}-\d{2}",
        r"\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}",
        r"\d{1,2}[-/]\d{1,2}[-/]\d{4}"
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return format_date(match.group(0))

    return "Date not listed"


def fetch_html_table(source):
    request = urllib.request.Request(
        source["url"], headers=HEADERS
    )

    with urllib.request.urlopen(request, timeout=25) as response:
        html = response.read().decode("utf-8", errors="replace")

    parser = TableParser()
    parser.feed(html)

    results = []

    for row_text, href, anchor_text in parser.rows[:40]:
        full_url = urljoin(source["url"], href)

        if not full_url.startswith("http"):
            continue

        if not (
            ".pdf" in full_url.lower()
            or "download" in full_url.lower()
            or len(anchor_text) > 15
        ):
            continue

        title = anchor_text if len(anchor_text) > 15 else row_text

        title = re.sub(r"^\d+\s*", "", title)
        title = re.sub(
            r"\d{4}-[A-Za-z]{3}-\d{2}|\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}",
            "",
            title
        )
        title = clean_text(title)

        if len(title) < 8:
            continue

        results.append({
            "category": source["category"],
            "title": title[:250],
            "summary": row_text[:400],
            "date": extract_date(row_text),
            "source": source["name"],
            "url": full_url,
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
        try:
            method = source.get("method")

            if method == "rss" and source.get("feed_url"):
                entries = fetch_feed(source)

            elif method == "html_table":
                entries = fetch_html_table(source)

            else:
                continue

            source_added = 0

            for item in entries:
                if item["url"] not in known_urls:
                    updates.append(item)
                    known_urls.add(item["url"])
                    added += 1
                    source_added += 1

            print(
                f"Checked: {source['name']} "
                f"| New items: {source_added}"
            )

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
