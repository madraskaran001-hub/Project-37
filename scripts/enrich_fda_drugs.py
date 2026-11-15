
import json
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent

INPUT = ROOT / "drug_candidates.json"
OUTPUT = ROOT / "fda_label_review.json"

API = "https://api.fda.gov/drug/label.json"

def get_label(application):
    query = urllib.parse.urlencode({
        "search": f'openfda.application_number:"{application}"',
        "limit": 5
    })

    request = urllib.request.Request(
        API + "?" + query,
        headers={
            "User-Agent": "Project37/1.0",
            "Accept": "application/json"
        }
    )

    try:
        with urllib.request.urlopen(
            request, timeout=30
        ) as response:
            data = json.load(response)
            return data.get("results", [])

    except urllib.error.HTTPError as error:
        if error.code == 404:
            return []
        raise

def first_section(label, key):
    values = label.get(key, [])
    if not isinstance(values, list):
        return ""
    return "\n".join(str(x) for x in values).strip()

def main():
    candidates = json.loads(
        INPUT.read_text(encoding="utf-8")
    )

    if not isinstance(candidates, list):
        raise ValueError("Expected a candidate list")

    existing = {}

    if OUTPUT.exists():
        previous = json.loads(
            OUTPUT.read_text(encoding="utf-8")
        )

        existing = {
            item["id"]: item
            for item in previous
            if isinstance(item, dict) and item.get("id")
        }

    checked = 0

    for candidate in candidates:
        application = candidate.get("application_number")
        candidate_id = candidate.get("id")

        if not application or not candidate_id:
            continue

        if candidate_id in existing:
            continue

        # Limit requests per run.
        if checked >= 10:
            break

        checked += 1

        try:
            labels = get_label(application)
        except Exception as error:
            print("Lookup failed:", application, error)
            continue

        if not labels:
            print("No matching label:", application)
            continue

        # Do not automatically assume that the first
        # matching label is the correct product.
        for label in labels:
            moa = first_section(label, "mechanism_of_action")
            uses = first_section(label, "indications_and_usage")
            adverse = first_section(label, "adverse_reactions")

            if not (moa and uses and adverse):
                continue

            label_id = label.get("id", "")
            record_id = candidate_id + ":" + label_id

            if record_id in existing:
                continue

            existing[record_id] = {
                "id": record_id,
                "candidate_id": candidate_id,
                "application_number": application,
                "label_id": label_id,
                "name": (
                    label.get("openfda", {})
                    .get("generic_name", [""])[0]
                ),
                "moa": moa,
                "use": uses,
                "adverse_effects": adverse,
                "source": "openFDA labeling",
                "source_url": (
                    "https://api.fda.gov/drug/label.json"
                    "?search=" +
                    urllib.parse.quote(
                        f'openfda.application_number:"{application}"'
                    )
                ),
                "review_status": "pending",
                "retrieved_at": datetime.now(
                    timezone.utc
                ).isoformat()
            }

    OUTPUT.write_text(
        json.dumps(
            list(existing.values()),
            indent=2,
            ensure_ascii=False
        ) + "\n",
        encoding="utf-8"
    )

    print("Records retrieved for review:", len(existing))
    print("No records were automatically verified.")
    print("Master Drug Library remains unchanged.")

if __name__ == "__main__":
    main()
