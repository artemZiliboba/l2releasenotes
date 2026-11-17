# NC Korea source capture (experimental)

This workflow is **read-only** and must be started manually in GitHub Actions. It retrieves the first 18 items from each of `l2update` and `l2note`, stores the original article API JSON, and downloads attached original files from the official NC CDN. Its output is an Actions artifact (`nc-korean-originals`) retained for 14 days, **not a commit, translation, PR, or Telegram publication**.

## Verified from browser HAR

- First list page: `GET https://api-community.plaync.com/lin2/board/l2update/article/search/moreArticle?isVote=true&moreSize=18&moreDirection=BEFORE&previousArticleId=0`
- List response has `contentList` and `hasMore`.
- Article details: `GET https://api-community.plaync.com/lin2/board/{board}/article/{articleId}`.
- `l2note` article attachments include an original infographic URL under `article.content.attachments.files`.
- The `l2update` article response includes the original HTML.

The first-page API call and article-detail structure were observed in browser HAR. Direct requests from GitHub-hosted runners and the `l2note` listing endpoint are **not yet independently tested**. The workflow may fail; this is an experiment.

## Limits and next verification

- Only the first page is supported. The exact cursor for subsequent pages has not been verified; do not assume the last article ID is a valid cursor.
- `serverFamily` is always `unverified`. Korean `본서버`, `BASIC`, and `말하는섬` are not presumed to mean Essence/Aden.
- `sha256` hashes the normalized article JSON; timestamps and counters may change without substantive editorial changes. Later compare canonical HTML/attachments separately.
- The script downloads source files for review; it does not perform OCR, translate, publish, or change `master`.
- Before scheduling automatic runs, verify pagination, access restrictions, terms of use, rate limits, change detection, and secure long-term storage.
- Do not add automatic Telegram posting until the reviewed translation is published on Pages and the link is confirmed accessible.

Run locally: `python scripts/collect_nc_sources.py --board l2update --output nc-capture`.


## Attachment reliability and failure reporting

The first GitHub Actions run on 2026-11-17 collected 18 article JSON responses per board but reported 13 CDN download failures: six HTTP 406 and seven HTTP 502. These are observed HTTP statuses, not proof of a specific root cause.

- HTTP 502, 503, 504, 500, 429 and 408, and transient network failures, receive up to three attempts with bounded backoff.
- HTTP 406 is **not retried**: it may represent an intentional server/CDN restriction. No circumvention or authentication spoofing is attempted.
- Each board's `manifest.json` records attachment counts and per-file errors, including HTTP status and official URL.
- Expected file sizes are checked when supplied by the API; a mismatched download counts as failed.
- The collector exits with status 1 if any requested attachment fails, but the workflow still uploads the partial archive via `if: always()`.
- The script is not considered complete until the artifact manifest shows `attachments.failed = 0` for each board. A green validation job does not prove source completeness.

If HTTP 406 persists, investigate NC's documented download policy and supported API options rather than attempting to bypass CDN restrictions.
