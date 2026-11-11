"""Build Project37's deduplicated master drug library."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ["drugs.json", "drug_catalog.json", "drug_topics.json", "project37_expansion.json"]


def categories(value):
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    return [str(value).strip()] if value else []


def normalize(record):
    return {
        "name": record.get("name", ""),
        "brand": record.get("brand", ""),
        "specialty": record.get("specialty", ""),
        "category": categories(record.get("category")),
        "use": record.get("use", ""),
        "moa": record.get("moa") or record.get("topic", ""),
        "adverse_effects": record.get("adverse_effects") or record.get("major_adverse_effects", ""),
        "exam_pearl": record.get("exam_pearl", ""),
        "approval_status": record.get("approval_status", ""),
        "approval_date": record.get("approval_date", ""),
        "source": record.get("source", ""),
    }


def main():
    merged = {}
    for filename in SOURCES:
        path = ROOT / filename
        if not path.exists():
            print(f"Skipping missing file: {filename}")
            continue
        records = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(records, list):
            raise ValueError(f"{filename} must contain a JSON array")
        for record in records:
            if not isinstance(record, dict):
                continue
            name = str(record.get("name") or "").strip()
            if not name:
                continue
            key = name.casefold()
            new = normalize(record)
            if key not in merged:
                merged[key] = new
                continue
            old = merged[key]
            old["category"] = list(dict.fromkeys(old["category"] + new["category"]))
            for field in old:
                if field != "category" and not old[field] and new[field]:
                    old[field] = new[field]
    output = sorted(merged.values(), key=lambda x: x["name"].casefold())
    (ROOT / "master_drugs.json").write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(output)} unique drugs to master_drugs.json")


if __name__ == "__main__":
    main()
