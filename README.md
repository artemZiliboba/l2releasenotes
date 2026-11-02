# L2 KR Release Notes

Unofficial Russian translations of Lineage 2 Essence / Aden patch notes.

## Status
Stage 1 in progress. Astro website, RSS, GitHub Pages workflow, validation workflow and a **reviewed manual import** are implemented. Automated Korean ingestion and translation are **not** implemented until the correct official source and terms are verified. No fabricated patches are included.

## Local
```bash
npm install
npm run dev
npm run build
python -m unittest discover -s tests -v
```

## Import a reviewed translation
Create a JSON file (outside the repo if preferred) with `source_id`, `source_url` (official NC Korea HTTPS), `date` (YYYY-MM-DD), `title`, `summary`, `body` (Markdown), `reviewed: true`, optional `version` and `categories` (array). The `reviewed` flag is an explicit human approval of correct version/source and translation. Run:

```bash
python scripts/import_patch.py reviewed.json
```

It generates a stable Markdown file in `src/content/patches/YYYY/` and skips identical reimports. This is an interim workflow, **not** an automated scraper or translator.

## GitHub Pages
After merging into `master`, configure Settings → Pages → Build and deployment → Source: GitHub Actions. `pages.yml` builds and deploys to https://artemZiliboba.github.io/l2releasenotes/ .

## Roadmap
- #1 Site, Korean source validation, ingestion, translation, deployment.
- #2 Telegram notifications (separate stage).
- See `docs/source-research.md` for source status.
