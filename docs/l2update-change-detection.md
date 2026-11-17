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

## Persistent observed-source registry (next MVP step)

The manual Action now reads `state/l2update.json` from a dedicated `state/l2update` Git branch. If the branch does not exist, the first successful run initializes it as the baseline. After a successful capture and artifact upload, the Action updates the state branch. Runs are serialized using GitHub Actions concurrency to prevent two jobs from overwriting each other.

The registry retains every observed article ID and its last seen **editorial content hash**, including articles that later leave the latest-18 window. On each run the artifact includes `editorial-diff.json` with `new`, `changed`, and `unchanged` classifications relative to the stored registry. If the registry cannot be read or written, the workflow fails rather than claiming that its comparison is durable. The workflow requires `contents: write` permission for the GitHub Actions token and repository settings must permit writing the dedicated branch.

**Safety boundary:** this is an *observed-source* registry, not a record of approved translations or published pages. It does not skip downloading the 18 JSON details (needed to detect silent edits), does not create PRs or publish, and does not yet check open PRs/Pages. Do not equate `unchanged` with `translated` or `published`. The initial 18 `new` records mean *new to the registry*, not *newly published today*.

The registry is intentionally separate from `master`; routine state writes must not trigger the Pages deployment workflow. The previous instructions describing the workflow as baseline-only are superseded by this section after the PR is merged and the first run succeeds.
