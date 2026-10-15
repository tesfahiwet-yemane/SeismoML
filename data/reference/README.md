# Reference catalogue (Yemane et al.)

Manually reviewed ARGOS catalogue used as the reference in notebooks 04 and 05.

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
| `magnitude` | ML | recommended |

## `picks.csv`

One row per analyst pick.

| column | unit |
|---|---|
| `event_id` | links to `catalogue.csv` |
| `station` | e.g. `A10E` |
| `phase` | `P` or `S` |
| `time` | ISO 8601 UTC |
