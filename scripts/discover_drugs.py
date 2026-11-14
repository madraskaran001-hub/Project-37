

import json
import urllib.request
from urllib.parse import urlencode
from pathlib import Path
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "drug_candidates.json"
API = "https://api.fda.gov/drug/drugsfda.json"

def fetch_records():
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=30)

    search = (
        "submissions.submission_status_date:"
        f"[{start:%Y%m%d} TO {today:%Y%m%d}]"
    )

    url = API + "?" + urlencode({
        "search": search,
        "limit": 99
    })

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Project37-MedicalIntelligence/1.0",
            "Accept": "application/json"
        }
    )

    with urllib.request.urlopen(request, timeout=40) as response:
        return json.load(response)["results"]

def load_existing():
    if not OUTPUT.exists():
        return {}

    data = json.loads(OUTPUT.read_text(encoding="utf-8"))

    if not isinstance(data, list):
        raise ValueError("Existing candidates file must be a list")

    return {
        item["id"]: item
        for item in data
        if isinstance(item, dict) and item.get("id")
    }

def main():
    existing = load_existing()
    records = fetch_records()
    now = datetime.now(timezone.utc).isoformat()

    for record in records:
        application = record.get("application_number", "")
        products = record.get("products", [])

        approved = [
            submission
            for submission in record.get("submissions", [])
            if submission.get("submission_status") == "AP"
            and submission.get("submission_type") == "ORIG"
        ]

        if not approved:
            continue

        for submission in approved:
            date = submission.get("submission_status_date", "")

            if len(date) != 8:
                continue

            candidate_id = (
                application + "-"
                + submission.get("submission_number", "")
            )

            if candidate_id in existing:
                continue

            existing[candidate_id] = {
                "id": candidate_id,
                "application_number": application,
                "products": [
                    {
                        "brand_name": p.get("brand_name", ""),
                        "active_ingredients": p.get(
                            "active_ingredients", []
                        )
                    }
                    for p in products
                ],
                "approval_date": date,
                "sponsor": record.get("sponsor_name", ""),
                "classification": submission.get(
                    "submission_class_code_description", ""
                ),
                "source": "FDA Drugs@FDA",
                "source_url": (
                    "https://www.accessdata.fda.gov/"
                    "scripts/cder/daf/"
                ),
                "review_status": "pending",
                "discovered_at": now
            }

    candidates = sorted(
        existing.values(),
        key=lambda item: item.get("approval_date", ""),
        reverse=True
    )

    OUTPUT.write_text(
        json.dumps(candidates, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8"
    )

    print(f"Saved {len(candidates)} candidate records")
    print("Master Drug Library was not modified.")

if __name__ == "__main__":
    main()
