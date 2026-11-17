#!/usr/bin/env python3
"""Capture official Korean Lineage 2 board data; never publish or translate it."""
import argparse
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API = "https://api-community.plaync.com/lin2/board"
BOARDS = ("l2update", "l2note")
HEADERS = {"User-Agent": "l2releasenotes-source-collector/0.1", "Accept": "application/json"}
SAFE_ID = re.compile(r"^[a-zA-Z0-9_-]{1,100}$")


def fetch(url, max_bytes=20_000_000):
    req = Request(url, headers=HEADERS)
    with urlopen(req, timeout=30) as response:
        data = response.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise ValueError("Response exceeds size limit")
        return data


def get_json(url):
    return json.loads(fetch(url).decode("utf-8"))


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def collect(board, output, size=18, pages=1, download_attachments=True):
    if board not in BOARDS:
        raise ValueError("Unsupported board")
    root = output / board
    root.mkdir(parents=True, exist_ok=True)
    cursor = "0"
    seen = set()
    records = []
    for page in range(pages):
        params = urlencode({"isVote": "true", "moreSize": size, "moreDirection": "BEFORE", "previousArticleId": cursor})
        listing = get_json(f"{API}/{board}/article/search/moreArticle?{params}")
        items = listing.get("contentList", [])
        if not isinstance(items, list):
            raise ValueError("Unexpected contentList")
        save_json(root / f"list-page-{page + 1}.json", listing)
        if not items:
            break
        for item in items:
            article_id = str(item.get("id", ""))
            if not SAFE_ID.fullmatch(article_id) or article_id in seen:
                continue
            seen.add(article_id)
            detail = get_json(f"{API}/{board}/article/{article_id}")
            article_dir = root / "articles" / article_id
            save_json(article_dir / "article.json", detail)
            meta = item.get("timestamps") or {}
            records.append({
                "id": article_id,
                "board": board,
                "title": item.get("title"),
                "postedAt": meta.get("postedAt"),
                "updatedAt": meta.get("updatedAt"),
                "sourceUrl": f"https://lineage2.plaync.com/board/{board}/view?articleId={article_id}",
                "sha256": hashlib.sha256(json.dumps(detail, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
                "serverFamily": "unverified",
            })
            if download_attachments:
                article = detail.get("article") or {}
                content = article.get("content") or {}
                attachments = (content.get("attachments") or {}).get("files") or []
                for index, attachment in enumerate(attachments):
                    url = attachment.get("fileUrl")
                    if not isinstance(url, str) or not url.startswith("https://fizz-download.playnccdn.com/"):
                        continue
                    mime = attachment.get("mimeType") or ""
                    suffix = { "image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp" }.get(mime, ".bin")
                    try:
                        raw = fetch(url, max_bytes=25_000_000)
                        dest = article_dir / "attachments" / f"{index:03d}{suffix}"
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        dest.write_bytes(raw)
                    except Exception as exc:
                        print(f"Attachment failed: {board}/{article_id}/{index}: {exc}", flush=True)
            print(f"{board}: {article_id} {item.get('title', '')}", flush=True)
            time.sleep(0.2)
        if not listing.get("hasMore") or page + 1 >= pages:
            break
        # The HAR confirms the first-page request only. Do not guess the cursor
        # for later pages; require an independently verified pagination contract.
        raise RuntimeError("Further pagination is not yet verified; run with --pages 1")
    save_json(root / "manifest.json", {
        "board": board,
        "collectedAt": datetime.now(timezone.utc).isoformat(),
        "records": records,
        "completeHistory": not bool(listing.get("hasMore")),
    })
    return len(records)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("nc-capture"))
    parser.add_argument("--board", choices=(*BOARDS, "all"), default="all")
    parser.add_argument("--size", type=int, default=18)
    parser.add_argument("--pages", type=int, default=1)
    parser.add_argument("--no-attachments", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.size <= 18 or args.pages != 1:
        parser.error("Only first-page collection (size 1..18, pages=1) is verified")
    for board in BOARDS if args.board == "all" else (args.board,):
        print(f"{board}: captured {collect(board, args.output, args.size, args.pages, not args.no_attachments)} articles")


if __name__ == "__main__":
    main()
