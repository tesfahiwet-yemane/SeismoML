#!/usr/bin/env python
"""Add (or refresh) the "Open in Colab" badge and the Colab setup cell in every notebook.

    python scripts/add_colab_cells.py

Safe to run repeatedly: existing Colab cells are replaced, nothing else is touched.
Edit COLAB_FLAGS below to change what each notebook downloads on Colab.
"""

from __future__ import annotations

import sys
from pathlib import Path

import nbformat

ROOT = Path(__file__).resolve().parents[1]
REPO = "tesfahiwet-yemane/SeismoML"
BRANCH = "main"

# What each notebook needs on a fresh Colab machine.
COLAB_FLAGS = {
    "00": "",
    "01": "--data",
    "02": "--data --outputs",
    "03": "--data --outputs",
    "04": "--data --outputs",
    "05": "--data --outputs",
}

SETUP = '''# Running on Google Colab? This cell installs everything and gets the data (2-4 minutes).
# On your own computer it does nothing.
import os, subprocess, sys
if "google.colab" in sys.modules:
    repo = "/content/SeismoML"
    if not os.path.isdir(repo):
        subprocess.run(["git", "clone", "--depth", "1", "https://github.com/{repo}.git", repo], check=True)
    subprocess.run([sys.executable, f"{{repo}}/scripts/colab_setup.py"] + "{flags}".split(), check=True)
    sys.path.insert(0, f"{{repo}}/src")
    os.chdir(f"{{repo}}/notebooks")'''


def tagged(cell, tag: str) -> bool:
    return tag in cell.get("metadata", {}).get("tags", [])


def process(path: Path) -> None:
    nb = nbformat.read(path, as_version=4)
    nb.cells = [c for c in nb.cells if not (tagged(c, "colab-badge") or tagged(c, "colab-setup"))]
    url = f"https://colab.research.google.com/github/{REPO}/blob/{BRANCH}/notebooks/{path.name}"
    badge = nbformat.v4.new_markdown_cell(
        f"[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)]({url})",
        metadata={"tags": ["colab-badge"]},
    )
    flags = COLAB_FLAGS.get(path.name[:2], "--data")
    setup = nbformat.v4.new_code_cell(SETUP.format(repo=REPO, flags=flags),
                                      metadata={"tags": ["colab-setup"]})
    # badge right after the title cell, setup cell before the first code cell
    first_code = next((i for i, c in enumerate(nb.cells) if c.cell_type == "code"), len(nb.cells))
    nb.cells.insert(first_code, setup)
    nb.cells.insert(1, badge)
    for i, c in enumerate(nb.cells):  # stable, unique ids
        c["id"] = c.get("id") or f"{path.name[:2]}-{i:03d}"
    nbformat.validate(nb)
    nbformat.write(nb, path)
    print("updated", path.name)


def main() -> int:
    for path in sorted((ROOT / "notebooks").glob("0*.ipynb")):
        process(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
