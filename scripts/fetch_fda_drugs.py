
import json
import time
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "fda_approvals.json"

API = "https://api.fda.gov/drug/drugsfda.json"


def fetch_page(skip, limit=100):
    params = urlencode({
        "limit": limit,
        "skip": skip
    })

    request = Request(
        API + "?" + params,
        headers={"User-Agent": "Project37/1.0"}
    )

    with urlopen(request, timeout=30) as response:
        return json.load(response)


def main():
    today = date.today()
    cutoff = today - timedelta(days=730)

    records = []
    seen = set()

    # Initial batch for testing connectivity and format.
    data = fetch_page(0)

    for item in data.get("results", []):
        application = item.get(
            "application_number", ""
        )

        products = item.get("products", [])

        for submission in item.get("submissions", []):
            raw_date = submission.get(
                "submission_status_date", ""
            )

            if len(raw_date) != 8 or not raw_date.isdigit():
                continue

            try:
                approval_date = date(
                    int(raw_date[:4]),
                    int(raw_date[4:6]),
                    int(raw_date[6:])
                )
            except ValueError:
                continue

            if not cutoff <= approval_date <= today:
                continue

            if submission.get("submission_status") != "AP":
                continue

            if submission.get("submission_type") != "ORIG":
                continue

            for product in products:
                name = product.get("drug_name", "")
                key = (application, name, raw_date)

                if not name or key in seen:
                    continue

                seen.add(key)

                records.append({
                    "name": name,
                    "application_number": application,
                    "approval_date": approval_date.isoformat(),
                    "regulator": "FDA",
                    "approval_type": "Original application",
                    "source": (
                        "https://www.accessdata.fda.gov/"
                        "scripts/cder/daf/"
                    )
                })

    records.sort(
        key=lambda x: x["approval_date"],
        reverse=True
    )

    OUTPUT.write_text(
        json.dumps(records, indent=2),
        encoding="utf-8"
    )

    print("PROJECT37 | FDA Import Test")
    print("Records collected:", len(records))
    print("Saved:", OUTPUT.name)
    print("Import test complete.")


if __name__ == "__main__":
    main()
