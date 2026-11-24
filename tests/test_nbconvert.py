"""Integration tests for the nbconvert preprocessor."""

import hashlib
import json
import sys

import pytest

nbformat = pytest.importorskip("nbformat")
pytest.importorskip("nbconvert")
pytest.importorskip("ipykernel")

from claimlink.nbconvert import ClaimLinkPreprocessor  # noqa: E402
from claimlink.storage import load  # noqa: E402


@pytest.fixture(autouse=True)
def _isolated_project(tmp_path, monkeypatch):
    monkeypatch.delenv("CLAIMLINK_ROOT", raising=False)
    monkeypatch.chdir(tmp_path)


@pytest.fixture
def kernel_name(tmp_path, monkeypatch):
    spec = tmp_path / "data" / "kernels" / "claimlink-test"
    spec.mkdir(parents=True)
    (spec / "kernel.json").write_text(
        json.dumps(
            {
                "argv": [
                    sys.executable,
                    "-m",
                    "ipykernel_launcher",
                    "-f",
                    "{connection_file}",
                ],
                "display_name": "claimlink test",
                "language": "python",
            }
        )
    )
    monkeypatch.setenv("JUPYTER_PATH", str(tmp_path / "data"))
    return "claimlink-test"


def _execute(cells, path, kernel_name, resources=None):
    nb = nbformat.v4.new_notebook(cells=cells)
    nbformat.write(nb, path / "experiment.ipynb")
    ClaimLinkPreprocessor(kernel_name=kernel_name, timeout=60).preprocess(
        nb, resources
    )
    return nb, load(path / "claim-lock.json")["claims"]


def _code(source):
    return nbformat.v4.new_code_cell(source)


def test_records_full_notebook_location(tmp_path, kernel_name):
    first = "from claimlink import claim\nclaim('papers', 3, unit='papers')\n"
    second = "claim('accuracy', 0.9)\n"

    nb, claims = _execute(
        [
            _code(first),
            nbformat.v4.new_markdown_cell("notes"),
            nbformat.v4.new_code_cell(""),
            _code(second),
        ],
        tmp_path,
        kernel_name,
        {"metadata": {"path": str(tmp_path), "name": "experiment"}},
    )

    assert claims["papers"]["location"] == {
        "type": "notebook",
        "file": "experiment.ipynb",
        "cell_id": nb.cells[0]["id"],
        "execution_count": 1,
        "line": 2,
        "cell_source_hash": hashlib.sha256(first.encode()).hexdigest(),
    }
    assert claims["accuracy"]["location"] == {
        "type": "notebook",
        "file": "experiment.ipynb",
        "cell_id": nb.cells[3]["id"],
        "execution_count": 2,
        "line": 1,
        "cell_source_hash": hashlib.sha256(second.encode()).hexdigest(),
    }
    for cell in nb.cells:
        for output in cell.get("outputs", []):
            assert "ClaimLocationUnavailableWarning" not in "".join(output.get("text", []))


def test_claim_in_another_cell_is_not_attributed_to_the_caller(tmp_path, kernel_name):
    cells = [
        _code("from claimlink import claim\n\ndef helper():\n    claim('helper claim', 1)\n"),
        _code("helper()\n"),
    ]

    nb, claims = _execute(
        cells,
        tmp_path,
        kernel_name,
        {"metadata": {"path": str(tmp_path), "name": "experiment"}},
    )

    location = claims["helper claim"]["location"]
    assert location["file"] == "experiment.ipynb"
    assert location["line"] == 4
    assert location["cell_id"] is None
    assert location["execution_count"] is None
    assert location["cell_source_hash"] is None
    warnings = "".join(
        "".join(output.get("text", [])) for output in nb.cells[1].get("outputs", [])
    )
    assert "different notebook cell" in warnings


def test_resources_are_optional(tmp_path, kernel_name):
    nb, claims = _execute(
        [_code("from claimlink import claim\nclaim('papers', 1)\n")],
        tmp_path,
        kernel_name,
        resources=None,
    )

    location = claims["papers"]["location"]
    assert location["file"] is None
    assert location["cell_id"] == nb.cells[0]["id"]
    warnings = "".join(
        "".join(output.get("text", [])) for output in nb.cells[0].get("outputs", [])
    )
    assert "filename is not available" in warnings
