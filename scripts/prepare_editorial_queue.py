#!/usr/bin/env python3
"""Build a review queue from captured Korean originals; never publish it."""
import argparse
import json
from pathlib import Path
from html.parser import HTMLParser


class SourceAudit(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables = 0
        self.rows = 0
        self.images = 0
        self.links = 0

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.tables += 1
        elif tag == "tr":
            self.rows += 1
        elif tag == "img":
            self.images += 1
        elif tag == "a":
            self.links += 1


def build_queue(capture):
    root = capture / "l2update"
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    queue = []
    for item in manifest["records"]:
        detail = json.loads((root / "articles" / item["id"] / "article.json").read_text(encoding="utf-8"))
        article = detail["article"]
        html = (article.get("content") or {}).get("content")
        if not isinstance(html, str) or not html.strip():
            raise ValueError(f"Missing complete HTML for {item['id']}")
        audit = SourceAudit()
        audit.feed(html)
        queue.append({
            "id": item["id"],
            "titleKorean": (article.get("contentMeta") or {}).get("title") or item["title"],
            "sourceUrl": item["sourceUrl"],
            "postedAt": item.get("postedAt"),
            "updatedAt": item.get("updatedAt"),
            "serverLabel": "unverified; preserve original Korean title",
            "originalFile": f"l2update/articles/{item['id']}/article.json",
            "audit": {"tables": audit.tables, "rows": audit.rows, "images": audit.images, "links": audit.links},
            "status": "awaiting_editorial_translation",
            "publishApproved": False,
        })
    return {"board": "l2update", "entries": queue, "note": "Editorial review queue only; no publishing approval."}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("capture", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = build_queue(args.capture)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Prepared {len(data['entries'])} editorial source records")


if __name__ == "__main__":
    main()
