
import json
from pathlib import Path
from datetime import date

ROOT = Path(__file__).resolve().parent.parent
DRUGS_FILE = ROOT / "drugs.json"

def main():
    drugs = json.loads(
        DRUGS_FILE.read_text(encoding="utf-8")
    )

    if not isinstance(drugs, list):
        raise ValueError("drugs.json must contain a list")

    cutoff = date(2024, 11, 9)
    today = date.today()

    recent = []
    historical = []

    for drug in drugs:
        approval = date.fromisoformat(drug["approval_date"])

        if cutoff <= approval <= today:
            recent.append(drug)
        else:
            historical.append(drug)

    print("project37 Drug Library")
    print("Recent drugs:", len(recent))
    print("Historical drugs:", len(historical))

if __name__ == "__main__":
    main()
