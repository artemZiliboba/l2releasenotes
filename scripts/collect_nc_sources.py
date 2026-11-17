#!/usr/bin/env python3
"""Capture official Korean Lineage 2 board data; never publish or translate it."""
import argparse
import hashlib
import random
import json
import re
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
from urllib.parse import urlencode, urlparse
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

API = "https://api-community.plaync.com/lin2/board"
BOARDS = ("l2update", "l2note")
HEADERS = {"User-Agent": "l2releasenotes-source-collector/0.1", "Accept": "application/json"}
RETRY_HTTP = {408, 429, 500, 502, 503, 504}
MAX_ATTEMPTS = 3
SAFE_ID = re.compile(r"^[a-zA-Z0-9_-]{1,100}$")


def fetch(url, max_bytes=20_000_000):
    req = Request(url, headers=HEADERS)
    with urlopen(req, timeout=30) as response:
        data = response.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise ValueError("Response exceeds size limit")
        return data


def fetch_attachment(url, max_bytes=25_000_000, sleep=time.sleep):
    """Retry temporary network failures, not policy rejections (e.g. HTTP 406)."""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return fetch(url, max_bytes=max_bytes), attempt
        except HTTPError as exc:
            if exc.code not in RETRY_HTTP or attempt == MAX_ATTEMPTS:
                raise
            delay = min(2 ** (attempt - 1), 8) + random.uniform(0, 0.3)
            print(f"CDN retry: HTTP {exc.code}, attempt {attempt}/{MAX_ATTEMPTS}", flush=True)
        except (URLError, TimeoutError) as exc:
            if attempt == MAX_ATTEMPTS:
                raise
            delay = min(2 ** (attempt - 1), 8) + random.uniform(0, 0.3)
            print(f"CDN retry: {type(exc).__name__}, attempt {attempt}/{MAX_ATTEMPTS}", flush=True)
        sleep(delay)
    raise RuntimeError("Unreachable retry state")


def get_json(url):
    return json.loads(fetch(url).decode("utf-8"))


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def is_in_month(item, month):
    """Filter by official posting timestamp in Korea local calendar month."""
    if month is None:
        return True
    timestamps = item.get("timestamps") or {}
    posted = timestamps.get("postedAt")
    if not isinstance(posted, str):
        raise ValueError("Missing postedAt; cannot safely filter by month")
    parsed = datetime.fromisoformat(posted.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Naive postedAt; cannot safely filter by month")
    return parsed.astimezone(ZoneInfo("Asia/Seoul")).strftime("%Y-%m") == month


def collect(board, output, size=18, pages=1, download_attachments=True, month=None):
    if board not in BOARDS:
        raise ValueError("Unsupported board")
    root = output / board
    root.mkdir(parents=True, exist_ok=True)
    cursor = "0"
    seen = set()
    records = []
    totals = {"expected": 0, "downloaded": 0, "failed": 0, "skipped": 0}
    errors = []
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
            if not is_in_month(item, month):
                continue
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
            article = detail.get("article") or {}
            content = article.get("content") or {}
            attachments = (content.get("attachments") or {}).get("files") or []
            for index, attachment in enumerate(attachments):
                totals["expected"] += 1
                url = attachment.get("fileUrl")
                if not download_attachments:
                    totals["skipped"] += 1
                    continue
                if not isinstance(url, str) or urlparse(url).hostname != "fizz-download.playnccdn.com" or not url.startswith("https://"):
                    totals["failed"] += 1
                    errors.append({"board": board, "articleId": article_id, "attachmentIndex": index,
                                   "error": "unsupported CDN URL", "status": None})
                    continue
                mime = attachment.get("mimeType") or ""
                suffix = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}.get(mime, ".bin")
                try:
                    raw, attempts = fetch_attachment(url)
                    expected_size = attachment.get("fileSize")
                    if isinstance(expected_size, int) and expected_size > 0 and len(raw) != expected_size:
                        raise ValueError(f"size mismatch: expected {expected_size}, got {len(raw)}")
                    dest = article_dir / "attachments" / f"{index:03d}{suffix}"
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(raw)
                    totals["downloaded"] += 1
                except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
                    status = exc.code if isinstance(exc, HTTPError) else None
                    totals["failed"] += 1
                    errors.append({"board": board, "articleId": article_id, "attachmentIndex": index,
                                   "status": status, "error": str(exc), "url": url})
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
        "monthFilter": month,
        "coverage": "first-list-page-only; month may be incomplete",
        "collectedAt": datetime.now(timezone.utc).isoformat(),
        "records": records,
        "completeHistory": not bool(listing.get("hasMore")),
        "attachments": totals,
        "attachmentErrors": errors,
    })
    print(f"{board}: attachments {totals['downloaded']}/{totals['expected']} downloaded; {totals['failed']} failed", flush=True)
    return len(records), totals['failed']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("nc-capture"))
    parser.add_argument("--board", choices=(*BOARDS, "all"), default="all")
    parser.add_argument("--size", type=int, default=18)
    parser.add_argument("--pages", type=int, default=1)
    parser.add_argument("--no-attachments", action="store_true")
    parser.add_argument("--month", help="Limit downloaded articles by Korean posting month (YYYY-MM)")
    args = parser.parse_args()
    if args.month and not re.fullmatch(r"[0-9]{4}-(0[1-9]|1[0-2])", args.month):
        parser.error("--month must be YYYY-MM")
    if not 1 <= args.size <= 18 or args.pages != 1:
        parser.error("Only first-page collection (size 1..18, pages=1) is verified")
    failures = 0
    for board in BOARDS if args.board == "all" else (args.board,):
        count, failed = collect(board, args.output, args.size, args.pages, not args.no_attachments, args.month)
        failures += failed
        print(f"{board}: captured {count} articles", flush=True)
    if failures:
        parser.exit(1, f"Incomplete capture: {failures} attachment(s) failed. Check manifests and uploaded artifact.\\n")


if __name__ == "__main__":
    main()
