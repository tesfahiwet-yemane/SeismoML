# Editing guide

Everything in this workshop is plain text or a standard Jupyter notebook. Edit any file, push
to GitHub, and the website is rebuilt automatically: GitHub Actions re-runs every notebook and
publishes the result. If a notebook raises an error, the build stops and the old website stays
online.

## Where things live

| To change… | Edit | Notes |
|---|---|---|
| Day, stations, region, depth range, network | `workshop.yml` | read by every notebook and script |
| Notebook text and code | `notebooks/0*.ipynb` | open in JupyterLab; see *Notebooks* below |
| Helper functions (picking, association, magnitudes, statistics, plots) | `src/seismoml/*.py` | documented, one topic per file |
| Home page, programme, setup, data pages | `docs/*.md` | Markdown |
| Website menu and title | `mkdocs.yml` | `nav:` and `site_name:` |
| Colours, fonts, layout | `docs/stylesheets/extra.css` | the palette is at the top |
| Logo | `docs/assets/logo.svg` | any SVG |
| Slides | `docs/slides/index.html` | Markdown inside the file; `---` starts a new slide, `Note:` adds speaker notes |
| Slide figures | `scripts/make_slide_figures.py` | redrawn from the real data on every build |
| Station table | `data/metadata/stations_argos.csv` | one row per deployment epoch |
| Velocity model | `data/models/aluto_wilks2017.csv` | layer tops in km b.s.l.; set the file in `workshop.yml` |
| Reference events and picks | `data/reference/nlloc/*.hyp` | then `python scripts/nlloc_to_csv.py` |
| Python versions | `requirements.txt` | pinned; CI uses exactly these |

## Notebooks

1. `jupyter lab notebooks/` and edit as usual.
2. Before committing, clear the outputs so the repository stays small (the website shows
   freshly executed copies anyway):

    ```bash
    jupyter nbconvert --clear-output --inplace notebooks/*.ipynb
    ```

3. Notebook 02 caches picks in `outputs/picks/`. After changing models or thresholds, set
   `RECOMPUTE = True` (or delete that folder).

## Preview the website before pushing

```bash
bash scripts/build_site.sh          # runs all notebooks, then serves http://127.0.0.1:8000
bash scripts/build_site.sh --fast   # only text changes: reuse executed notebooks
```

## Publish

```bash
git add -A
git commit -m "Describe your change"
git push
```

Then follow the run under **Actions** on GitHub. A green tick means the site is updated.

## Using another dataset

1. Edit `workshop.yml`: `network`, `stations`, `day`, `region`, `utm_epsg`, `demo_station`.
2. Replace the station table and the velocity model in `data/`.
3. Put your reference `.hyp` files in `data/reference/nlloc/` and run
   `python scripts/nlloc_to_csv.py`. Alternatively, write `catalogue.csv` and `picks.csv`
   directly (format in `data/reference/README.md`).
4. Delete `data/sds`, `data/inventory` and `outputs`, then run `python scripts/download_data.py`.
5. Change `archive.url` in `workshop.yml` (or leave it: the scripts fall back to FDSN).
