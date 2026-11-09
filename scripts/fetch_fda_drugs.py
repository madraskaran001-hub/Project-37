
import json
import time
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "fda_approvals.json"

API = "https://api.fda.gov/drug/drugsfda.json"
PAGE_SIZE = 100
MAX_PAGES = 10


def fetch_page(search, skip):
    params = urlencode({
        "search": search,
        "limit": PAGE_SIZE,
        "skip": skip
    })

    request = Request(
        API + "?" + params,
        headers={
            "User-Agent": "Project37/1.0",
            "Accept": "application/json"
        }
    )

    for attempt in range(3):
        try:
            with urlopen(request, timeout=40) as response:
                return json.load(response)
        except (HTTPError, URLError, TimeoutError) as error:
            print("Request failed:", error)
            if attempt == 2:
                raise
            time.sleep(3 * (attempt + 1))


def main():
    today = date.today()
    cutoff = today - timedelta(days=730)

    start = cutoff.strftime("%Y%m%d")
    end = today.strftime("%Y%m%d")

    search = (
        f"submissions.submission_status_date:"
        f"[{start}+TO+{end}]"
    )

    records = {}
    total_checked = 0

    for page in range(MAX_PAGES):
        skip = page * PAGE_SIZE

        print("Fetching page:", page + 1)

        data = fetch_page(search, skip)
        results = data.get("results", [])

        if not results:
            break

        total_checked += len(results)

        for item in results:
            application = item.get(
                "application_number", ""
            )

            submissions = item.get(
                "submissions", []
            )

            original_dates = []

            for submission in submissions:
                if submission.get(
                    "submission_type"
                ) != "ORIG":
                    continue

                if submission.get(
                    "submission_status"
                ) != "AP":
                    continue

                raw = submission.get(
                    "submission_status_date", ""
                )

                if len(raw) != 8 or not raw.isdigit():
                    continue

                try:
                    approved = date(
                        int(raw[:4]),
                        int(raw[4:6]),
                        int(raw[6:])
                    )
                except ValueError:
                    continue

                if cutoff <= approved <= today:
                    original_dates.append(approved)

            if not original_dates:
                continue

            approved = min(original_dates)

            for product in item.get("products", []):
                name = product.get(
                    "drug_name", ""
                ).strip()

                if not name:
                    continue

                key = (application, name)

                records[key] = {
                    "name": name,
                    "application_number": application,
                    "approval_date": approved.isoformat(),
                    "regulator": "FDA",
                    "approval_type": "Original application",
                    "source": (
                        "https://www.accessdata.fda.gov/"
                        "scripts/cder/daf/"
                    )
                }

        if len(results) < PAGE_SIZE:
            break

        time.sleep(1)

    output_records = sorted(
        records.values(),
        key=lambda x: x["approval_date"],
        reverse=True
    )

    print("FDA applications checked:", total_checked)
    print("Approval records found:", len(output_records))

    if not output_records:
        raise RuntimeError(
            "No FDA approval records found. "
            "Existing database was not overwritten."
        )

    temporary = OUTPUT.with_suffix(".tmp")

    temporary.write_text(
        json.dumps(output_records, indent=2),
        encoding="utf-8"
    )

    temporary.replace(OUTPUT)

    print("Saved:", OUTPUT.name)
    print("FDA import completed.")


if __name__ == "__main__":
    main()
