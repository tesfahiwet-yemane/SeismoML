# Programme, October 2026

Department of Earth Sciences, University of Oxford.

| Time | Session | Notebook |
|---|---|---|
| 09:30 | Welcome, environment check, coffee | `setup` |
| 09:45 | **Talk:** from STA/LTA to transformers. How ML pickers work and fail ([slides](slides/index.html)) | |
| 10:15 | Getting ARGOS data: FDSN, StationXML, SDS | 00 |
| 10:45 | *Coffee break* | |
| 11:00 | Denoising: band-pass vs. DeepDenoiser | 01 |
| 11:40 | Phase picking: VolPick vs. general-purpose weights | 02 |
| 12:45 | *Lunch* | |
| 13:45 | Association, location and ML with PyOcto | 03 |
| 14:45 | Validation against the analyst catalogue | 04 |
| 15:30 | *Coffee break* | |
| 15:45 | Seismicity analysis: Mc, b-value, clusters and planes | 05 |
| 16:45 | **Discussion:** what changes for volcano monitoring when catalogues grow 10×? | |
| 17:15 | Close | |
{ .aml-schedule }

!!! info "Shorter format"
    For a 1–2 hour lecture or tutorial, use
    [06 · Quick start](notebooks/06_quickstart_catalogue.ipynb): download, picking, association
    and NonLinLoc export in one notebook.

!!! tip "Before the day"
    Please complete the [setup](setup.md) **before** the workshop. Run
    `python scripts/fetch_data.py` and `python scripts/fetch_models.py` (data and model
    weights, so you do not depend on the venue Wi-Fi), then open notebook 00 to check that
    everything works.

!!! note "Long computations"
    Picking 24 h × 11 stations with six models takes 10–30 minutes on a laptop CPU. Notebook 02
    caches its picks in `outputs/picks/`. If time is short during the session, start it at the
    beginning of the coffee break, or reduce the number of models.
