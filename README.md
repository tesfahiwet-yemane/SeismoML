# SeismoML, Machine Learning for Seismology

[![Build notebooks and website](https://github.com/tesfahiwet-yemane/SeismoML/actions/workflows/build.yml/badge.svg)](https://github.com/tesfahiwet-yemane/SeismoML/actions/workflows/build.yml)
[![Website](https://img.shields.io/badge/website-online-e8590c)](https://tesfahiwet-yemane.github.io/SeismoML/)
![Python 3.12](https://img.shields.io/badge/python-3.12-24313d)
[![License: MIT](https://img.shields.io/badge/code-MIT-8a98a6)](LICENSE)

A one-day, hands-on workshop on machine learning and deep learning for seismic phase picking 
and earthquake detection, **October 2026**.

Starting from raw continuous waveforms, participants build a complete machine-learning
earthquake catalogue and validate it against analyst picks and locations. The case study is
the ARGOS network (FDSN code `XM`) at Aluto volcano, Main Ethiopian Rift, on 15 November 2012:

```
FDSN download → denoising → phase picking → association & location → ML magnitudes → validation → statistics
```

The central question: **does a picker trained on volcanic earthquakes (VolPick) beat
general-purpose models at Aluto?**

**Website with all executed notebooks:** <https://tesfahiwet-yemane.github.io/SeismoML/>

## Notebooks

Click a Colab badge to run a notebook in your browser: nothing to install.

| # | Notebook | Topics |
|---|---|---|
| 00 | [`00_data_access.ipynb`](https://colab.research.google.com/github/tesfahiwet-yemane/SeismoML/blob/main/notebooks/00_data_access.ipynb) [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/tesfahiwet-yemane/SeismoML/blob/main/notebooks/00_data_access.ipynb) | FDSN, StationXML, instrument response, SDS archive |
| 01 | [`01_denoising.ipynb`](https://colab.research.google.com/github/tesfahiwet-yemane/SeismoML/blob/main/notebooks/01_denoising.ipynb) [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/tesfahiwet-yemane/SeismoML/blob/main/notebooks/01_denoising.ipynb) | spectral band selection, DeepDenoiser, SNR, effect on picking |
| 02 | [`02_phase_picking.ipynb`](https://colab.research.google.com/github/tesfahiwet-yemane/SeismoML/blob/main/notebooks/02_phase_picking.ipynb) [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/tesfahiwet-yemane/SeismoML/blob/main/notebooks/02_phase_picking.ipynb) | PhaseNet & EQTransformer, VolPick vs. general-purpose weights |
| 03 | [`03_association.ipynb`](https://colab.research.google.com/github/tesfahiwet-yemane/SeismoML/blob/main/notebooks/03_association.ipynb) [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/tesfahiwet-yemane/SeismoML/blob/main/notebooks/03_association.ipynb) | PyOcto, Aluto 1D model, local magnitude (Keir et al., 2006) |
| 04 | [`04_catalogue_comparison.ipynb`](https://colab.research.google.com/github/tesfahiwet-yemane/SeismoML/blob/main/notebooks/04_catalogue_comparison.ipynb) [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/tesfahiwet-yemane/SeismoML/blob/main/notebooks/04_catalogue_comparison.ipynb) | recall, residuals and event matching against analyst picks |
| 05 | [`05_seismicity_analysis.ipynb`](https://colab.research.google.com/github/tesfahiwet-yemane/SeismoML/blob/main/notebooks/05_seismicity_analysis.ipynb) [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/tesfahiwet-yemane/SeismoML/blob/main/notebooks/05_seismicity_analysis.ipynb) | Mc (MAXC, MBS), b-value + bootstrap, DBSCAN, PCA planes |

## Quick start

```bash
git clone https://github.com/tesfahiwet-yemane/SeismoML.git && cd SeismoML
conda env create -f environment.yml && conda activate seismoml   # or: pip install -r requirements.txt -e .
pytest -q                          # fast checks, no network
python scripts/fetch_data.py       # one day of ARGOS data (release archive, or FDSN fallback)
jupyter lab notebooks/
```

## Repository layout

```
workshop.yml            single configuration file (day, stations, region, paths)
notebooks/              the six workshop notebooks (stored without outputs)
src/seismoml/           helper package used by the notebooks
scripts/                data download, archive packing, day ranking
data/metadata/          ARGOS deployment table
data/models/            Aluto 1D velocity model (Wilks et al., 2017)
data/reference/         reference catalogue + analyst picks (from NonLinLoc .hyp files in nlloc/)
tests/                  unit tests (b-value, PCA, matching, association, ...)
docs/                   website sources (MkDocs Material)
```

## Editing

Everything is plain text or a standard notebook and can be edited directly. See
[`docs/editing.md`](docs/editing.md) (also on the website) for where each piece lives and how
to preview your changes.

## Data

Waveforms: ARGOS network (XM, 2012–2014), archived at the EarthScope/IRIS DMC. Please cite the
network DOI and the papers listed on the website when using these data.

## Licence

Code: MIT. Text and figures: CC BY 4.0.
