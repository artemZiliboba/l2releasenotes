#!/usr/bin/env python3
"""Notify Telegram only when an NCSoft archive commit adds or changes article bodies."""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTICLES = "source-snapshots/l2update/articles/"


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True)


def previous_article(path):
    try:
        return json.loads(git("show", "HEAD^:" + path))
    except subprocess.CalledProcessError:
        return None


def body(obj):
    if not isinstance(obj, dict):
        return None
    article = obj.get("article") or {}
    content = article.get("content") or {}
    return content.get("content")


def main():
    if not os.environ.get("TELEGRAM_BOT_TOKEN") or not os.environ.get("TELEGRAM_CHAT_ID"):
        print("Telegram secrets unavailable; archive saved, notification skipped")
        return
    changes = git("diff", "--name-only", "HEAD^", "HEAD", "--", ARTICLES).splitlines()
    new, updated = [], []
    for path in changes:
        if not path.startswith(ARTICLES) or not path.endswith(".json"):
            continue
        current = json.loads((ROOT / path).read_text(encoding="utf-8"))
        original = previous_article(path)
        if original is not None and body(original) == body(current):
            continue
        title = str((current.get("record") or {}).get("title") or current.get("article_id"))
        url = current.get("source_url") or "https://lineage2.plaync.com/board/l2update"
        entry = title + "\n" + url
        (new if original is None else updated).append(entry)
    if not new and not updated:
        print("No new or changed Korean article bodies")
        return
    # Keep Telegram messages below its 4096-character limit.
    from telegram_notify import telegram
    entries = [("🆕 Новый оригинал", item) for item in new] + [
        ("🔄 Изменён оригинал", item) for item in updated
    ]
    chunk = "🇰🇷 NCSoft: изменения корейских оригиналов\n"
    for label, item in entries:
        line = "\n" + label + "\n" + item + "\n"
        if len(chunk) + len(line) > 3800:
            telegram(chunk)
            chunk = "🇰🇷 NCSoft: продолжение\n"
        chunk += line
    if chunk.strip():
        telegram(chunk)
    print(f"Notified: {len(new)} new, {len(updated)} updated")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Archive notifier failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
