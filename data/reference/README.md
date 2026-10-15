# Reference catalogue (Yemane et al.)

Manually reviewed ARGOS events used as the reference in notebooks 04 and 05.

**Source of truth: the NonLinLoc files in `nlloc/`.** `catalogue.csv` and `picks.csv` are
generated from them; do not edit the CSVs by hand. To add or update events, copy `.hyp`
files into `nlloc/` and run

```bash
python scripts/nlloc_to_csv.py              # all files in data/reference/nlloc/
python scripts/nlloc_to_csv.py --min-weight 0.1   # stricter: drop down-weighted phases
```

Locations are the NonLinLoc maximum-likelihood hypocentres; phases the locator weighted
below `--min-weight` (default 0.05) are dropped. NonLinLoc files carry no magnitudes, so
notebook 04 computes ML for these events with the same procedure as for the ML catalogue.
For notebook 05 (statistics), a longer catalogue (e.g. all 2012–2014 events) gives robust
results; a `magnitude` column, if present, is used.

> Yemane, T., Hudson, T. S., Kendall, J.-M., Blundy, J., Tadesse, A. Z., Hammond, J. O. S.,
> Ayele, A., Ogubazghi, G., & Lapins, S. Interconnectivity of magmatic and hydrothermal
> systems of Aluto volcano in the Main Ethiopian Rift inferred from seismicity.

## `catalogue.csv`

One row per event. Times are UTC in ISO 8601. Depth is in km **below sea level**.

| column | unit | required |
|---|---|---|
| `event_id` | integer, unique | yes |
| `time` | ISO 8601, e.g. `2012-11-15T03:21:07.430Z` | yes |
| `latitude`, `longitude` | degrees | yes |
| `depth_km` | km b.s.l. | yes |
| `magnitude` | ML | optional |
| `rms_s`, `n_phases`, `gap_deg`, `min_dist_km`, `err_h_km`, `err_max_km` | location quality | optional |

## `picks.csv`

One row per analyst pick.

| column | unit |
|---|---|
| `event_id` | links to `catalogue.csv` |
| `station` | e.g. `A10E` |
| `phase` | `P` or `S` |
| `time` | ISO 8601 UTC |
| `residual_s`, `weight` | NonLinLoc residual and weight (optional) |
