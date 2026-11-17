#!/usr/bin/env python3
"""Compare two NC capture manifests using meaningful editorial fields only.

This tool does not publish, translate, or assert server-family identity.
"""
import argparse
import hashlib
import json
from pathlib import Path


def editorial_payload(detail):
    article = detail.get("article") or {}
    content = article.get("content") or {}
    # Never hash the full API response: counters and engagement metadata vary.
    return {
        "title": article.get("title"),
        "html": content.get("content"),
        "attachments": [
            {"fileUrl": f.get("fileUrl"), "fileSize": f.get("fileSize")}
            for f in (content.get("attachments") or {}).get("files", [])
        ],
    }


def content_hash(detail):
    payload = editorial_payload(detail)
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def load_capture(root):
    manifest = json.loads((root / "l2update" / "manifest.json").read_text(encoding="utf-8"))
    result = {}
    for item in manifest["records"]:
        article_id = item["id"]
        detail_path = root / "l2update" / "articles" / article_id / "article.json"
        detail = json.loads(detail_path.read_text(encoding="utf-8"))
        result[article_id] = {
            "id": article_id,
            "title": item.get("title"),
            "sourceUrl": item.get("sourceUrl"),
            "postedAt": item.get("postedAt"),
            "updatedAt": item.get("updatedAt"),
            "contentHash": content_hash(detail),
            "serverFamily": "unverified",
        }
    return result


def compare(current, previous):
    records = []
    for article_id, item in current.items():
        old = previous.get(article_id)
        status = "new" if old is None else ("changed" if old["contentHash"] != item["contentHash"] else "unchanged")
        records.append({**item, "status": status})
    return records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("current", type=Path, help="Current nc-capture directory")
    parser.add_argument("--previous", type=Path, help="Earlier nc-capture directory; omit for baseline")
    parser.add_argument("--output", type=Path, help="JSON report path")
    args = parser.parse_args()
    current = load_capture(args.current)
    previous = load_capture(args.previous) if args.previous else {}
    records = compare(current, previous)
    report = {
        "board": "l2update",
        "baseline": args.previous is None,
        "records": records,
        "counts": {status: sum(r["status"] == status for r in records) for status in ("new", "changed", "unchanged")},
        "warning": "First-page window only. No publication or translation eligibility implied.",
    }
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
