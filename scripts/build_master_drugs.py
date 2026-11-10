
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FILES = [
    "drugs.json",
    "drug_catalog.json",
    "drug_topics.json"
]

OUTPUT = ROOT / "master_drugs.json"


def load_records(filename):
    path = ROOT / filename

    if not path.exists():
        print("Missing:", filename)
        return []

    data = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(data, list):
        raise ValueError(f"{filename} must contain a list")

    return data


def normalize(drug):
    return {
        "name": drug.get("name", ""),
        "brand": drug.get("brand", ""),
        "specialty": drug.get("specialty", ""),
        "category": drug.get("category", []),
        "use": drug.get("use", ""),
        "moa": drug.get("moa") or drug.get("topic", ""),
        "adverse_effects": (
            drug.get("adverse_effects")
            or drug.get("major_adverse_effects", "")
        ),
        "exam_pearl": drug.get("exam_pearl", ""),
        "approval_status": drug.get("approval_status", ""),
        "approval_date": drug.get("approval_date", ""),
        "source": drug.get("source", "")
    }


def main():
    combined = {}

    for filename in FILES:
        records = load_records(filename)

        for drug in records:
            if not isinstance(drug, dict):
                continue

            name = str(drug.get("name", "")).strip()

            if not name:
                continue

            key = name.casefold()
            normalized = normalize(drug)

            if key not in combined:
                combined[key] = normalized
                continue

            existing = combined[key]

            for field, value in normalized.items():
                if field == "category":
                    old = existing.get("category", [])
                    old = old if isinstance(old, list) else [old]
                    new = value if isinstance(value, list) else [value]

                    existing["category"] = list(
                        dict.fromkeys(old + new)
                    )

                elif not existing.get(field) and value:
                    existing[field] = value

    result = sorted(
        combined.values(),
        key=lambda drug: drug["name"].casefold()
    )

    OUTPUT.write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print("PROJECT37 MASTER DRUG LIBRARY")
    print("-----------------------------")
    print("Unique drugs:", len(result))
    print("Saved:", OUTPUT.name)


if __name__ == "__main__":
    main()
