#!/usr/bin/env python3
"""Save official NCSoft list records to GitHub-readable source snapshots.

This is a source acquisition stage, NOT a translation or publication engine.
The list endpoint does not guarantee complete article bodies. Never label list
metadata as a complete article.
"""
import datetime as dt
import hashlib
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "source-snapshots" / "l2update"
API_BASE = "https://api-community.plaync.com/lin2/board/l2update"\nAPI = API_BASE + "/article/search/moreArticle?isVote=true&moreSize=18&moreDirection=BEFORE&previousArticleId=0"


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; l2releasenotes-source-archive/1.0)", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=40) as response:
        return json.load(response)


def write_if_changed(path, obj):
    content = json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.write_text(content, encoding="utf-8")
    return True


def main():
    data = get_json(API)
    if not isinstance(data, dict) or not isinstance(data.get("contentList"), list) or not data["contentList"]:
        raise ValueError("Unexpected or empty official NCSoft contentList; no snapshot saved")
    entries = data["contentList"]
    ids = set()
    for item in entries:
        if not isinstance(item, dict):
            raise ValueError("Invalid NCSoft entry")
        article_id = item.get("articleId") or item.get("id")
        if not isinstance(article_id, (str, int)) or not str(article_id).strip():
            raise ValueError(f"NCSoft entry lacks recognized ID; keys={sorted(item)}")
        article_id = str(article_id)
        if not article_id.isalnum():
            raise ValueError("Unsafe NCSoft article ID")
        ids.add(article_id)
        detail = get_json(API_BASE + "/article/" + article_id)\n        article = detail.get("article") if isinstance(detail, dict) else None\n        body = (article.get("content") or {}).get("content") if isinstance(article, dict) else None\n        if not isinstance(body, str) or not body.strip():\n            raise ValueError(f"Full NCSoft article HTML missing for {article_id}; no incomplete snapshot will be committed")\n        write_if_changed(OUT / "articles" / (article_id + ".json"), {
            "source": "official NCSoft l2update list API",
            "article_id": article_id,
            "source_url": "https://lineage2.plaync.com/board/l2update/view?articleId=" + article_id,
            "record": item,
            "full_article_verified": True,
            "article": article,
            "note": "Full official article detail, including HTML body."
        })
    write_if_changed(OUT / "latest.json", {
        "source": API,
        "article_ids": sorted(ids),
        "count": len(entries),
        "has_more": data.get("hasMore"),
        "search_count": data.get("searchCount"),
        "full_article_verified": True,
    })
    print(f"Archived {len(entries)} official NCSoft article detail responses with HTML.")


if __name__ == "__main__":
    main()
