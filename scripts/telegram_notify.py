#!/usr/bin/env python3
"""Telegram notifications for successfully deployed patch notes and daily source checks."""
import argparse
import datetime as dt
import json
import html
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
    try:
        with urllib.request.urlopen(req, timeout=25) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read(2048).decode("utf-8", errors="replace")
        # Never expose a Telegram bot token, which is embedded in its request URL.
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from None


def telegram(text, html_mode=False):
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat = os.environ["TELEGRAM_CHAT_ID"]
    payload = urllib.parse.urlencode({"chat_id": chat, "text": text, "disable_web_page_preview": "true", **({"parse_mode": "HTML"} if html_mode else {})}).encode()
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
    names = git("diff", "--name-only", "--diff-filter=AM", before, after, "--", "src/content/patches")
    added = [ROOT / name for name in names.splitlines() if name.endswith(".md")]
    newly_added = set(git("diff", "--name-only", "--diff-filter=A", before, after, "--", "src/content/patches").splitlines())
    if not added:
        print("No new patch files")
        return
    records = [metadata(p) for p in added if p.is_file()]
    records = [r for r in records if r.get("title")]
    if not records:
        return
    for path, record in zip([p for p in added if p.is_file()], [metadata(p) for p in added if p.is_file()]):
        if not record.get("title"):
            continue
        title = str(record["title"])
        summary = str(record.get("summary", "")).strip()
        source = str(record.get("source_url", "")).strip()
        date = str(record.get("date", "")).strip()
        version = str(record.get("version", "")).replace("NC Korea · ", "").strip()
        # Astro glob loader uses the filename without its .md extension as the entry ID.
        article_id = path.relative_to(ROOT / "src/content/patches").with_suffix("").as_posix()
        article_url = SITE + "/patches/" + urllib.parse.quote(article_id, safe="/") + "/"
        short_title = re.sub(r"^\d{1,2}\.\d{1,2}\.\d{4}\s*[-—–]\s*", "", title)
        short_title = re.sub(r"^(?:Main|BASIC|Talking Island)\s*:\s*", "", short_title, flags=re.I)
        try:
            pretty_date = dt.date.fromisoformat(date).strftime("%d.%m.%Y")
        except ValueError:
            pretty_date = date
        lines = ["<b>" + ("🆕 Русский перевод опубликован" if str(path.relative_to(ROOT)) in newly_added else "✅ Русский перевод обновлён") + "</b>", ""]
        if pretty_date:
            lines.append("📅 " + html.escape(pretty_date))
        if version:
            lines.append("🎮 <b>" + html.escape(version) + "</b>")
        lines.append("")
        lines.append("<b>" + html.escape(short_title) + "</b>")
        if summary:
            lines.append("")
            lines.append(html.escape(summary[:230]))
        links = '<a href="' + html.escape(article_url, quote=True) + '">📖 Читать перевод</a>'
        if source.startswith("https://"):
            links += '  ·  <a href="' + html.escape(source, quote=True) + '">🇰🇷 Оригинал</a>'
        lines.extend(["", links])
        telegram("\n".join(lines), html_mode=True)


def ids_from_api(obj):
    """Read IDs from NCSoft's contentList, rejecting unexpected response formats."""
    if not isinstance(obj, dict) or not isinstance(obj.get("contentList"), list):
        raise ValueError("Unexpected NCSoft API response: contentList is missing")
    items = obj["contentList"]
    if not items:
        raise ValueError("NCSoft returned an empty contentList; cannot confirm no news")
    found = set()
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Unexpected NCSoft article entry type")
        # NCSoft search entries may use id rather than articleId.
        value = item.get("articleId") or item.get("id")
        if not isinstance(value, (str, int)) or not str(value).strip():
            keys = sorted(item.keys())
            raise ValueError(f"NCSoft entry has no recognized ID; available fields: {keys}")
        found.add(str(value))
    return found


def daily(args):
    # A single daily status message, not one per manual run.
    current = ids_from_api(request(NC_API))
    published = {str(m.get("source_id")) for p in articles() if (m := metadata(p)).get("source_id")}
    missing = current - published
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=3))).strftime("%d.%m.%Y %H:%M МСК")
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
