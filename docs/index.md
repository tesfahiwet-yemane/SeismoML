---
hide:
  - navigation
  - toc
---

<div class="aml-hero" markdown>

<p class="aml-meta">Department of Earth Sciences · University of Oxford · Geophysics group · 22 October 2026</p>

# Machine Learning<br>for Seismology

<p>A one-day, hands-on workshop. Starting from raw continuous waveforms, we build a complete
earthquake catalogue with open-source deep-learning tools, test it against analyst picks and
locations, and finish with the statistics and structure of the seismicity.</p>

<p class="aml-meta">Case study · ARGOS network (XM), Aluto volcano, Main Ethiopian Rift · 15 November 2012</p>

[Start with setup :material-rocket-launch:](setup.md){ .md-button .md-button--primary }
[Programme :material-clock-outline:](schedule.md){ .md-button }
[Notebooks :material-notebook-outline:](notebooks/00_data_access.ipynb){ .md-button }

</div>

<div class="aml-pipeline">
<span>FDSN download</span><span class="arrow">➜</span>
<span>Denoising</span><span class="arrow">➜</span>
<span>Phase picking</span><span class="arrow">➜</span>
<span>Association &amp; location</span><span class="arrow">➜</span>
<span>Magnitudes</span><span class="arrow">➜</span>
<span>Validation</span><span class="arrow">➜</span>
<span>Statistics &amp; structure</span>
</div>

## Why this workshop?

Deep-learning phase pickers now produce catalogues 5–10 times larger than manual ones, and
they do it in minutes. Most public models, however, were trained on tectonic earthquakes.
**Volcanoes are different:** shallow sources, strongly scattering media, emergent onsets and
long-period events. This workshop asks a practical question on real data from a
geothermal-volcanic system (Aluto, Main Ethiopian Rift):

!!! question "Does a picker trained on volcanic earthquakes (VolPick) beat general-purpose models at Aluto, and how do we know?"

## The notebooks

<div class="grid cards" markdown>

-   <span class="aml-step">00</span> **Data access**

    ---
    FDSN web services, StationXML and instrument responses, SDS archives. Download ARGOS data
    yourself.

    [:octicons-arrow-right-24: Open](notebooks/00_data_access.ipynb)

-   <span class="aml-step">01</span> **Denoising**

    ---
    Data-driven band-pass vs. DeepDenoiser. Measure the SNR gain, and test whether it changes
    what a picker finds.

    [:octicons-arrow-right-24: Open](notebooks/01_denoising.ipynb)

-   <span class="aml-step">02</span> **Phase picking**

    ---
    PhaseNet and EQTransformer with general-purpose and **VolPick** weights, on 11 stations ×
    24 h. Calibration, agreement and timing bias.

    [:octicons-arrow-right-24: Open](notebooks/02_phase_picking.ipynb)

-   <span class="aml-step">03</span> **Association**

    ---
    PyOcto with the Aluto 1D velocity model, preliminary locations and Main Ethiopian Rift
    local magnitudes.

    [:octicons-arrow-right-24: Open](notebooks/03_association.ipynb)

-   <span class="aml-step">04</span> **Validation**

    ---
    Pick-level recall and residuals against analyst picks; event matching, location and
    magnitude differences.

    [:octicons-arrow-right-24: Open](notebooks/04_catalogue_comparison.ipynb)

-   <span class="aml-step">05</span> **Seismicity analysis**

    ---
    Completeness (MAXC, MBS), maximum-likelihood b-values with bootstrap, DBSCAN clusters and
    PCA fault-plane fits.

    [:octicons-arrow-right-24: Open](notebooks/05_seismicity_analysis.ipynb)

</div>

## What you will need

* A laptop with Python 3.12, through conda or `venv` ([setup guide](setup.md)). A GPU is **not** needed.
* About 3 GB of free disk space: the environment, the model weights and one day of waveforms.
* Familiarity with Python, NumPy/pandas and basic seismology (P/S phases, travel times).

## Software at the core

[SeisBench](https://github.com/seisbench/seisbench) ·
[VolPick](https://github.com/zhong-yy/volpick) ·
[PyOcto](https://github.com/yetinam/pyocto) ·
[ObsPy](https://github.com/obspy/obspy) ·
[PyTorch](https://pytorch.org) ·
[scikit-learn](https://scikit-learn.org)

!!! info "Every page is executed"
    The notebooks on this site are run from start to finish on every change by GitHub
    Actions, with the pinned environment in `requirements.txt`. What you see is what you will
    get on your laptop.

!!! tip "Reusing the material"
    Everything is driven by one configuration file, `workshop.yml`. Change the network,
    stations, day and region there to run the same pipeline on another dataset. See the
    [editing guide](editing.md).
