#!/usr/bin/env python3
"""Telegram alerts for meaningful changes to official Korean NCSoft article bodies."""
import datetime as dt
import difflib
import html
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
ARTICLES = "source-snapshots/l2update/articles/"
SITE = "https://artemziliboba.github.io/l2releasenotes"
MSK = ZoneInfo("Europe/Moscow")


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def previous_article(path):
    try:
        return json.loads(git("show", "HEAD^:" + path))
    except subprocess.CalledProcessError:
        return None


def body(obj):
    if not isinstance(obj, dict):
        return None
    return ((obj.get("article") or {}).get("content") or {}).get("content")


class TextBlocks(HTMLParser):
    """Keep paragraph/list/table boundaries, ignoring non-content markup."""
    BLOCKS = {"p", "div", "li", "tr", "td", "th", "h1", "h2", "h3", "h4", "br"}
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.hidden += 1
        if tag in self.BLOCKS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.hidden = max(0, self.hidden - 1)
        if tag in self.BLOCKS:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def blocks(raw):
    if not isinstance(raw, str):
        return []
    parser = TextBlocks()
    parser.feed(raw)
    lines = []
    for line in "".join(parser.parts).splitlines():
        line = re.sub(r"\s+", " ", html.unescape(line)).strip()
        if line and (not lines or line != lines[-1]):
            lines.append(line)
    return lines


def published_links():
    result = {}
    for path in (ROOT / "src/content/patches").rglob("*.md"):
        data = path.read_text(encoding="utf-8")
        head = data.split("---", 2)[1] if data.startswith("---") else ""
        match = re.search(r'^source_id:\s*["\']?([a-zA-Z0-9]+)', head, re.M)
        if match:
            slug = path.relative_to(ROOT / "src/content/patches").with_suffix("").as_posix()
            result[match.group(1)] = SITE + "/patches/" + slug + "/"
    return result


def summary(old, new):
    """Describe actual text-level additions/removals; never invent a translation."""
    a, b = blocks(old), blocks(new)
    if a == b:
        return None
    changes = []
    added = removed = 0
    for operation, i, j, k, l in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if operation == "equal":
            continue
        added += l - k
        removed += j - i
        for line in b[k:l][:3]:
            changes.append("＋ " + line[:180])
        for line in a[i:j][:2]:
            changes.append("− " + line[:180])
    if not changes:
        return None
    detail = "\n".join(html.escape(x) for x in changes[:5])
    if len(changes) > 5:
        detail += f"\n… и ещё {len(changes) - 5} строк"
    return f"Изменения в тексте: добавлено {added}, удалено {removed} строк(и).\n{detail}"


def send_alerts():
    from telegram_notify import telegram
    changes = git("diff", "--name-only", "HEAD^", "HEAD", "--", ARTICLES).splitlines()
    links = published_links()
    alerts = []
    for path in changes:
        if not path.startswith(ARTICLES) or not path.endswith(".json"):
            continue
        current = json.loads((ROOT / path).read_text(encoding="utf-8"))
        previous = previous_article(path)
        current_body = body(current)
        if not isinstance(current_body, str) or not current_body.strip():
            print(f"Skipping incomplete original: {path}")
            continue
        old_body = body(previous)
        if previous is not None and old_body == current_body:
            continue
        source_id = str(current.get("article_id") or Path(path).stem)
        record = current.get("record") or {}
        title = str(record.get("title") or source_id)
        source = current.get("source_url") or ("https://lineage2.plaync.com/board/l2update/view?articleId=" + source_id)
        new = previous is None
        delta = summary(old_body, current_body) if not new else None
        if not new and delta is None:
            print(f"Only HTML/formatting changed: {source_id}")
            continue
        status = "🆕 Новый корейский оригинал" if new else "🔄 Изменён корейский оригинал"
        lines = [f"<b>{status}</b>", "", "🇰🇷 <b>" + html.escape(title) + "</b>", ""]
        if new:
            lines.append("Обнаружена новая статья NCSoft. Полный русский перевод ещё не опубликован.")
        else:
            lines.extend(["<b>Что изменилось в оригинале:</b>", delta,
                          "", "Фрагменты выше приведены на языке оригинала; автоматический перевод не выполнялся."])
        translated = links.get(source_id)
        if translated:
            lines.extend(["", "⏳ Русская статья существует, но новая редакция ещё не подтверждена.",
                          '<a href="' + html.escape(translated, quote=True) + '">🇷🇺 Текущий перевод</a>'])
        else:
            lines.extend(["", "⏳ Русский перевод пока не опубликован."])
        lines.append('<a href="' + html.escape(source, quote=True) + '">🇰🇷 Оригинал NCSoft</a>')
        lines.append("🕒 " + dt.datetime.now(MSK).strftime("%d.%m.%Y %H:%M МСК"))
        alerts.append("\n".join(lines))
    for message in alerts:
        if len(message) > 3900:
            message = message[:3800] + "\n…\n</b>" if False else message[:3800] + "\n…"
        telegram(message, html_mode=True)
    print(f"Sent {len(alerts)} meaningful NCSoft change alert(s)")


def main():
    if not os.environ.get("TELEGRAM_BOT_TOKEN") or not os.environ.get("TELEGRAM_CHAT_ID"):
        print("Telegram secrets unavailable; notification skipped")
        return
    send_alerts()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Archive notifier failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
