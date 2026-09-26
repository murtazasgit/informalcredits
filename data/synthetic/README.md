# Synthetic dataset — split by credit category and user

The combined files (`demographics.json`, `transactions.csv`, `product_catalog.json`) are the API's fallback data source.
The same 20 users are also split into one folder each, grouped by the rule engine's risk band:

```
data/synthetic/<poor|fair|good>/user_<n>/
    demographics.json     this user's profile (one-element list — uploads as-is)
    transactions.csv      this user's own transactions
    expected_score.json   engine score, band, 14-factor breakdown and features
```

No synthetic user reaches the Excellent band (>= 800), so there is no `excellent/` folder.
Upload any user folder's two files to `POST /upload-raw` (or the dashboard) to reproduce `expected_score.json`.
Regenerate with `python data/split_synthetic.py` (deterministic).

| Category | Folder | User ID | Score | Tier | Employment |
|---|---|---|---|---|---|
| poor | `poor/user_1` | U1001 | 360 | tier-2 | self-employed |
| poor | `poor/user_2` | U1010 | 340 | tier-2 | full-time |
| fair | `fair/user_1` | U1002 | 535 | tier-1 | gig-platform |
| fair | `fair/user_2` | U1004 | 440 | tier-3 | gig-platform |
| fair | `fair/user_3` | U1008 | 575 | tier-2 | freelance |
| fair | `fair/user_4` | U1009 | 595 | tier-3 | gig-platform |
| fair | `fair/user_5` | U1011 | 530 | tier-1 | self-employed |
| fair | `fair/user_6` | U1015 | 530 | tier-2 | self-employed |
| fair | `fair/user_7` | U1016 | 495 | tier-1 | self-employed |
| fair | `fair/user_8` | U1018 | 540 | tier-3 | part-time |
| fair | `fair/user_9` | U1020 | 560 | tier-1 | self-employed |
| good | `good/user_1` | U1003 | 645 | tier-3 | gig-platform |
| good | `good/user_2` | U1005 | 625 | tier-1 | full-time |
| good | `good/user_3` | U1006 | 750 | tier-3 | gig-platform |
| good | `good/user_4` | U1007 | 645 | tier-2 | part-time |
| good | `good/user_5` | U1012 | 695 | tier-1 | full-time |
| good | `good/user_6` | U1013 | 675 | tier-1 | full-time |
| good | `good/user_7` | U1014 | 610 | tier-1 | freelance |
| good | `good/user_8` | U1017 | 735 | tier-3 | freelance |
| good | `good/user_9` | U1019 | 700 | tier-1 | full-time |
