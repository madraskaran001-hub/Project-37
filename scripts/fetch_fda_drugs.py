

import json
from pathlib import Path
from datetime import date, timedelta

ROOT = Path(__file__).resolve().parent.parent
DRUGS_FILE = ROOT / "drugs.json"


def validate_drug(drug):
    if not isinstance(drug, dict):
        print("Invalid drug record")
        return False

    required = [
        "name",
        "approval_date",
        "regulator",
        "use",
        "moa",
        "major_adverse_effects"
    ]

    missing = [
        field for field in required
        if not drug.get(field)
    ]

    if missing:
        print(
            "Incomplete record:",
            drug.get("name", "Unknown")
        )
        print("Missing:", ", ".join(missing))
        return False

    try:
        date.fromisoformat(drug["approval_date"])
    except (ValueError, TypeError):
        print(
            "Invalid approval date:",
            drug["name"]
        )
        return False

    return True


def main():
    drugs = json.loads(
        DRUGS_FILE.read_text(encoding="utf-8")
    )

    if not isinstance(drugs, list):
        raise ValueError("drugs.json must contain a list")

    today = date.today()
    cutoff = today - timedelta(days=730)

    recent = []
    historical = []
    invalid = 0

    for drug in drugs:
        if not validate_drug(drug):
            invalid += 1
            continue

        approval = date.fromisoformat(
            drug["approval_date"]
        )

        if cutoff <= approval <= today:
            recent.append(drug)
        else:
            historical.append(drug)

    print("PROJECT37 | Drug Library")
    print("------------------------")
    print("Total records:", len(drugs))
    print("Recent drugs:", len(recent))
    print("Historical drugs:", len(historical))
    print("Invalid records:", invalid)
    print("Database validation complete.")


if __name__ == "__main__":
    main()
