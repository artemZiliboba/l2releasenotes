#!/usr/bin/env python3
"""Telegram notifications for successfully deployed patch notes and daily source checks."""
import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = "https://artemziliboba.github.io/l2releasenotes"
NC_API = "https://api-community.plaync.com/lin2/board/l2update/article/search/moreArticle?isVote=true&moreSize=18&moreDirection=BEFORE&previousArticleId=0"


def request(url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": "l2releasenotes-notifier/1.0", **(headers or {})})
    with urllib.request.urlopen(req, timeout=25) as response:
        return json.load(response)


def telegram(text):
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat = os.environ["TELEGRAM_CHAT_ID"]
    payload = urllib.parse.urlencode({"chat_id": chat, "text": text, "disable_web_page_preview": "true"}).encode()
    request(f"https://api.telegram.org/bot{token}/sendMessage", data=payload)


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def articles():
    return sorted((ROOT / "src/content/patches").rglob("*.md"))


def metadata(path):
    raw = path.read_text(encoding="utf-8")
    if not raw.startswith("---\n"):
        return {}
    head = raw.split("---", 2)[1]
    result = {}
    for line in head.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        if key in {"title", "summary", "source_id", "date", "version", "source_url"}:
            try:
                result[key] = json.loads(value.strip())
            except json.JSONDecodeError:
                result[key] = value.strip().strip('"')
    return result


def deployed(args):
    # The caller checks that the Pages workflow concluded successfully.
    before = args.before
    after = args.after
    if not before or not after or before == after:
        print("No new deployment delta")
        return
    names = git("diff", "--name-only", "--diff-filter=A", before, after, "--", "src/content/patches")
    added = [ROOT / name for name in names.splitlines() if name.endswith(".md")]
    if not added:
        print("No new patch files")
        return
    records = [metadata(p) for p in added if p.is_file()]
    records = [r for r in records if r.get("title")]
    if not records:
        return
    lines = [f"🆕 Опубликованы переводы Lineage 2 Korea: {len(records)}"]
    for record in records:
        title = record["title"]
        summary = str(record.get("summary", "")).strip()
        source = record.get("source_url", "")
        date = record.get("date", "")
        lines.append(f"\n• {date} — {title}")
        if summary:
            lines.append(summary[:230])
        # Link to site root is guaranteed; avoid inventing Astro slug URLs.
        lines.append(f"Сайт: {SITE}/")
        if source:
            lines.append(f"Оригинал: {source}")
    telegram("\n".join(lines)[:3900])


def ids_from_api(obj):
    """Fail closed when NCSoft changes response schema; never report a false no-news."""
    found = set()
    def walk(value):
        if isinstance(value, dict):
            if "articleId" in value and isinstance(value["articleId"], (str, int)):
                found.add(str(value["articleId"]))
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)
    walk(obj)
    if not found:
        raise ValueError("NCSoft API returned no recognizable article IDs")
    return found


def daily(args):
    # A single daily status message, not one per manual run.
    current = ids_from_api(request(NC_API))
    published = {str(m.get("source_id")) for p in articles() if (m := metadata(p)).get("source_id")}
    missing = current - published
    now = dt.datetime.now(dt.timezone.utc).strftime("%d.%m.%Y %H:%M UTC")
    if missing:
        telegram(f"📋 Проверка L2 Update — {now}\nВ последних {len(current)} записях NCSoft найдено {len(missing)} ID, которых пока нет среди опубликованных статей сайта.\nЭто не означает, что все относятся к целевой версии или ещё не переведены.\nИсточник: https://lineage2.plaync.com/board/l2update")
    else:
        telegram(f"✅ Проверка L2 Update — {now}\nНовых неопубликованных записей среди последних {len(current)} статей NCSoft не обнаружено.")


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="mode", required=True)
    p = sub.add_parser("deployed")
    p.add_argument("--before", required=True)
    p.add_argument("--after", required=True)
    sub.add_parser("daily")
    args = parser.parse_args()
    try:
        if args.mode == "deployed":
            deployed(args)
        else:
            daily(args)
    except Exception as exc:
        print(f"Notifier failed: {exc}", file=sys.stderr)
        if args.mode == "daily" and os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID"):
            try:
                telegram(f"⚠️ Проверка L2 Update завершилась ошибкой: {type(exc).__name__}. Новизна обновлений не подтверждена.")
            except Exception as send_exc:
                print(f"Could not notify error: {send_exc}", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
