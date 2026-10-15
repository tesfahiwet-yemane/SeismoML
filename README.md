# Machine Learning for Seismicity at Aluto Volcano

[![Build notebooks and website](https://github.com/OWNER/REPO/actions/workflows/build.yml/badge.svg)](https://github.com/OWNER/REPO/actions/workflows/build.yml)
[![Website](https://img.shields.io/badge/website-online-e8590c)](https://OWNER.github.io/REPO/)
![Python 3.12](https://img.shields.io/badge/python-3.12-24313d)
[![License: MIT](https://img.shields.io/badge/code-MIT-8a98a6)](LICENSE)

A one-day, hands-on workshop for the Geophysics group, Department of Earth Sciences,
University of Oxford, on **22 October 2026**.

Starting from raw broadband waveforms of the ARGOS network (FDSN code `XM`) at Aluto volcano
in the Main Ethiopian Rift, participants build a complete machine-learning earthquake
catalogue and validate it against an analyst catalogue:

```
FDSN download → denoising → phase picking → association & location → ML magnitudes → validation → statistics
```

The central question: **does a picker trained on volcanic earthquakes (VolPick) beat
general-purpose models at Aluto?**

**Website with all executed notebooks:** <https://OWNER.github.io/REPO/>

## Notebooks

| # | Notebook | Topics |
|---|---|---|
| 00 | `00_data_access.ipynb` | FDSN, StationXML, instrument response, SDS archive |
| 01 | `01_denoising.ipynb` | spectral band selection, DeepDenoiser, SNR, effect on picking |
| 02 | `02_phase_picking.ipynb` | PhaseNet & EQTransformer, VolPick vs. general-purpose weights |
| 03 | `03_association.ipynb` | PyOcto, Aluto 1D model, local magnitude (Keir et al., 2006) |
| 04 | `04_catalogue_comparison.ipynb` | recall, residuals and event matching against analyst picks |
| 05 | `05_seismicity_analysis.ipynb` | Mc (MAXC, MBS), b-value + bootstrap, DBSCAN, PCA planes |

## Quick start

```bash
git clone https://github.com/OWNER/REPO.git workshop && cd workshop
conda env create -f environment.yml && conda activate aluto-ml   # or: pip install -r requirements.txt -e .
pytest -q                          # fast checks, no network
python scripts/fetch_data.py       # one day of ARGOS data (release archive, or FDSN fallback)
jupyter lab notebooks/
```

## Repository layout

```
workshop.yml            single configuration file (day, stations, region, paths)
notebooks/              the six workshop notebooks (stored without outputs)
src/alutoml/            helper package used by the notebooks
scripts/                data download, archive packing, day ranking
data/metadata/          ARGOS deployment table
data/models/            Aluto 1D velocity model (Wilks et al., 2017)
data/reference/         reference catalogue and analyst picks (Yemane et al.)
tests/                  unit tests (b-value, PCA, matching, association, ...)
docs/                   website sources (MkDocs Material)
```

## Data

Waveforms: ARGOS network (XM, 2012–2014), archived at the EarthScope/IRIS DMC. Please cite the
network DOI and the papers listed on the website when using these data.

## Licence

Code: MIT. Text and figures: CC BY 4.0.
