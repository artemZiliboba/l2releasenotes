# Manual-first translation workflow

Until the official Korean Essence/Aden source mapping is verified, do not enable unattended scraping or publishing.

1. Copy the Korean text **from a confirmed relevant official source** into a local UTF-8 JSON file, e.g.
   `{"source_id":"official-article-id","source_url":"https://lineage2.plaync.com/...","date":"2026-11-02","korean_title":"...","korean_body":"...","version":"Essence"}`.
2. Set `OPENAI_API_KEY` in your local environment. Never commit keys or raw private configuration.
3. Run `python scripts/translate_patch.py korean.json --output draft.json`.
4. Review **all** sections, tables, percentages, Korean item names and source/version accuracy. The generated draft is marked `reviewed: false` and cannot be imported.
5. Once verified, explicitly set `reviewed: true` and run `python scripts/import_patch.py draft.json`.
6. Commit the resulting Markdown and let GitHub Pages build it after merging.

Caveats: the translator is a single-pass prototype and rejects Korean bodies longer than 50,000 characters; a production pipeline needs chunking, completeness checks, retries and source change detection. No automatic Telegram publishing is implemented.
