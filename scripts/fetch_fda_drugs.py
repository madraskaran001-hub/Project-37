
import json
import time
from datetime import date, timedelta
from calendar import monthrange
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
            with urlopen(request, timeout=45) as response:
                return json.load(response)

        except HTTPError as error:
            if error.code == 404:
                return {"results": []}

            print("FDA HTTP error:", error.code)

            if error.code not in (429, 500, 502, 503, 504):
                raise

        except (URLError, TimeoutError) as error:
            print("Connection error:", error)

        if attempt < 2:
            time.sleep(3 * (attempt + 1))

    raise RuntimeError("FDA API unavailable")


def month_ranges(start, end):
    current = date(start.year, start.month, 1)

    while current <= end:
        last_day = monthrange(
            current.year, current.month
        )[1]

        month_end = date(
            current.year, current.month, last_day
        )

        yield max(current, start), min(month_end, end)

        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(
                current.year, current.month + 1, 1
            )


def main():
    today = date.today()
    cutoff = today - timedelta(days=730)

    records = {}
    checked = 0

    for start_date, end_date in month_ranges(cutoff, today):
        print(
            "Checking:",
            start_date.isoformat(),
            "to",
            end_date.isoformat()
        )

        start = start_date.strftime("%Y%m%d")
        end = end_date.strftime("%Y%m%d")

        search = (
            "submissions.submission_type:ORIG"
            "+AND+"
            "submissions.submission_status:AP"
            "+AND+"
            f"submissions.submission_status_date:[{start}+TO+{end}]"
        )

        for page in range(MAX_PAGES):
            data = fetch_page(
                search,
                page * PAGE_SIZE
            )

            results = data.get("results", [])

            if not results:
                break

            checked += len(results)

            for item in results:
                application = item.get(
                    "application_number", ""
                )

                for submission in item.get(
                    "submissions", []
                ):
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

                    if not cutoff <= approved <= today:
                        continue

                    for product in item.get(
                        "products", []
                    ):
                        name = product.get(
                            "drug_name", ""
                        ).strip()

                        if not name:
                            continue

                        key = (application, name, raw)

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

            time.sleep(0.3)

    output = sorted(
        records.values(),
        key=lambda item: item["approval_date"],
        reverse=True
    )

    print("Applications checked:", checked)
    print("Approval records found:", len(output))

    if not output:
        raise RuntimeError(
            "No approvals found. Existing database preserved."
        )

    temporary = OUTPUT.with_suffix(".tmp")

    temporary.write_text(
        json.dumps(output, indent=2),
        encoding="utf-8"
    )

    temporary.replace(OUTPUT)

    print("Saved:", OUTPUT.name)
    print("FDA import completed successfully.")


if __name__ == "__main__":
    main()


