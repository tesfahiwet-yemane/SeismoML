# Setup

There are two ways to follow the workshop.

!!! success "Option A · Google Colab: nothing to install"
    Open any notebook with its **Open in Colab** badge (at the top of each notebook, or in
    the table below) and run the first cell. It installs the packages and downloads the data
    in 2–4 minutes. You only need a Google account and a browser.

    * Each notebook runs on its own fresh Colab machine. Notebooks 02–05 therefore download
      the picks and catalogues produced by the latest website build, so they work on their
      own. To compute everything yourself, set `RECOMPUTE = True` in notebook 02.
    * **Runtime → Change runtime type → T4 GPU** makes picking much faster (optional).
    * Colab sessions are temporary. Use **File → Save a copy in Drive** to keep your changes.

    | Notebook | |
    |---|---|
    | 00 · Data access | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/tesfahiwet-yemane/SeismoML/blob/main/notebooks/00_data_access.ipynb) |
    | 01 · Denoising | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/tesfahiwet-yemane/SeismoML/blob/main/notebooks/01_denoising.ipynb) |
    | 02 · Phase picking | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/tesfahiwet-yemane/SeismoML/blob/main/notebooks/02_phase_picking.ipynb) |
    | 03 · Association | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/tesfahiwet-yemane/SeismoML/blob/main/notebooks/03_association.ipynb) |
    | 04 · Validation | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/tesfahiwet-yemane/SeismoML/blob/main/notebooks/04_catalogue_comparison.ipynb) |
    | 05 · Seismicity analysis | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/tesfahiwet-yemane/SeismoML/blob/main/notebooks/05_seismicity_analysis.ipynb) |
    | 06 · Quick start (1–2 h) | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/tesfahiwet-yemane/SeismoML/blob/main/notebooks/06_quickstart_catalogue.ipynb) |

## Option B · Your own computer

The workshop uses a **pinned** Python 3.12 environment. The same versions are used to execute
the notebooks on this website.

### 1 · Get the material

```bash
cd ~/Documents
git clone https://github.com/tesfahiwet-yemane/SeismoML.git
cd SeismoML
```

### 2 · Create the environment

=== "conda / mamba (recommended)"

    ```bash
    conda env create -f environment.yml
    conda activate seismoml
    ```

=== "venv + pip"

    ```bash
    python3.12 -m venv .venv
    source .venv/bin/activate          # Windows: .venv\Scripts\activate
    pip install -r requirements.txt -e .
    ```

=== "Linux, small CPU-only PyTorch"

    ```bash
    pip install --extra-index-url https://download.pytorch.org/whl/cpu \
        -r requirements.txt -e .
    ```

Check the installation:

```bash
pytest -q          # fast unit tests, no network needed
```

### 3 · Get the data

```bash
python scripts/fetch_data.py
```

This downloads the pre-packed day of ARGOS waveforms and the StationXML from the GitHub
release. If that is not available, it falls back to the EarthScope/IRIS FDSN service. Data end
up in `data/sds/` (SDS layout) and `data/inventory/`.

Notebooks 04–05 also need the reference catalogue and analyst picks in `data/reference/`
(`catalogue.csv`, `picks.csv`; format in `data/reference/README.md`).

### 4 · Start Jupyter

```bash
jupyter lab notebooks/
```

and open `00_data_access.ipynb`.

## Troubleshooting

??? failure "`asyncio.run() cannot be called from a running event loop`"
    SeisBench patches Jupyter's event loop when it is imported. Make sure `import seisbench`
    (or `import seisbench.models`) runs in the notebook itself. Do not import it from a
    start-up script.

??? failure "Weights download fails or hangs"
    The notebooks switch automatically to SeisBench's backup mirror (GFZ Potsdam) when the main
    repository is unreachable. To avoid depending on the network at all, download every model
    in advance with `python scripts/fetch_models.py`. The weights are cached in `~/.seisbench`. Behind a proxy, set `HTTPS_PROXY`. To use another
    cache location, set `SEISBENCH_CACHE_ROOT` before starting Jupyter.

??? failure "`pyocto` fails to install"
    Wheels exist for Python 3.10–3.12 on Linux, macOS and Windows. With Python 3.13 pip would
    build it from source and needs a C++ compiler. Use Python 3.12 as pinned.

??? question "Do I need a GPU?"
    No. Everything runs on a laptop CPU. With an NVIDIA GPU, call `model.cuda()` after
    loading a picker to make picking a day about 10× faster.
