# Setup

The workshop uses a **pinned** Python 3.12 environment. The same versions are used to execute
the notebooks on this website.

## 1 · Get the material

```bash
cd ~/Documents
git clone https://github.com/OWNER/REPO.git workshop
cd workshop
```

## 2 · Create the environment

=== "conda / mamba (recommended)"

    ```bash
    conda env create -f environment.yml
    conda activate aluto-ml
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

## 3 · Get the data

```bash
python scripts/fetch_data.py
```

This downloads the pre-packed day of ARGOS waveforms and the StationXML from the GitHub
release. If that is not available, it falls back to the EarthScope/IRIS FDSN service. Data end
up in `data/sds/` (SDS layout) and `data/inventory/`.

Notebooks 04–05 also need the reference catalogue and analyst picks in `data/reference/`
(`catalogue.csv`, `picks.csv`; format in `data/reference/README.md`).

## 4 · Start Jupyter

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
    The weights are cached in `~/.seisbench`. Behind a proxy, set `HTTPS_PROXY`. To use another
    cache location, set `SEISBENCH_CACHE_ROOT` before starting Jupyter.

??? failure "`pyocto` fails to install"
    Wheels exist for Python 3.10–3.12 on Linux, macOS and Windows. With Python 3.13 pip would
    build it from source and needs a C++ compiler. Use Python 3.12 as pinned.

??? question "Do I need a GPU?"
    No. Everything runs on a laptop CPU. With an NVIDIA GPU, call `model.cuda()` after
    loading a picker to make picking a day about 10× faster.
