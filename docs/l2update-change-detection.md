# L2 Update editorial change detection (MVP step)

The capture Action collects only the newest 18 L2 Update articles. It now includes `editorial-diff.json` in the artifact. On the first run, without an earlier snapshot, all entries are classified `new` **relative to an empty baseline**, not necessarily newly published.

## Comparing two captures

Download and unpack two Action artifacts into separate directories:

```bash
python scripts/compare_nc_capture.py ./current-capture --previous ./previous-capture --output ./diff.json
```

The report assigns each article ID `new`, `changed`, or `unchanged`. It hashes article title, HTML body, and attachment URL/size rather than the whole API response, avoiding false changes from view counters and other response metadata.

**Important limits:** The workflow currently has no durable previous snapshot, so its generated report is a **baseline only**. Comparison with a previous capture is manual until durable state is implemented. It still downloads the latest 18 article JSONs on each run. This is *not yet* end-to-end deduplication of translation PRs, Pages, or Telegram notifications. Hashes detect source-content differences but do not establish translation completeness, server-family identity, or authorization to publish. Existing articles falling outside the 18-item window cannot be checked for edits.

The next implementation step is to retain the prior editorial fingerprint manifest across Action runs and cross-check open PRs and published pages before translation.
