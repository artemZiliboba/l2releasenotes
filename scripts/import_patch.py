#!/usr/bin/env python3
"""Import a reviewed Russian translation from JSON; no scraping or automatic publication."""
import argparse
import hashlib
import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "src/content/patches"

def import_patch(record: dict, output: Path = OUTPUT) -> Path:
    required = ("source_id", "source_url", "date", "title", "summary", "body")
    for key in required:
        if not isinstance(record.get(key), str) or not record[key].strip():
            raise ValueError(f"Missing non-empty field: {key}")
    if urlparse(record["source_url"]).scheme != "https" or urlparse(record["source_url"]).hostname not in {"lineage2.plaync.com", "lounge.plaync.com", "about.ncsoft.com"}:
        raise ValueError("Only official NC Korean HTTPS sources are allowed")
    date.fromisoformat(record["date"])
    if not isinstance(record.get("categories", []), list) or not all(isinstance(x, str) for x in record.get("categories", [])):
        raise ValueError("categories must be a list of strings")
    if record.get("reviewed") is not True:
        raise ValueError("A human must review the source/version and translation before publishing")
    slug = hashlib.sha256(record["source_url"].encode()).hexdigest()[:16]
    path = output / record["date"][:4] / f"{record['date']}-{slug}.md"
    metadata = {k: record[k] for k in ("title", "date", "summary", "source_url", "source_id")}
    metadata["version"] = record.get("version", "Essence")
    metadata["categories"] = record.get("categories", [])
    # JSON string literals are valid YAML scalars; avoid injecting raw frontmatter.
    frontmatter = "\n".join(f"{k}: {json.dumps(v, ensure_ascii=False)}" for k,v in metadata.items())
    content = f"---\n{frontmatter}\n---\n\n{record['body'].strip()}\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return path
    path.write_text(content, encoding="utf-8")
    return path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("json_file", type=Path)
    args = parser.parse_args()
    record = json.loads(args.json_file.read_text(encoding="utf-8"))
    print(import_patch(record))

if __name__ == "__main__":
    main()
