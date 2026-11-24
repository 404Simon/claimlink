"""nbconvert integration: give the kernel the notebook path and cell id."""

from pathlib import Path

from nbconvert.preprocessors import ExecutePreprocessor

# Variable read by claimlink.location inside the kernel.
MARKER = "__claimlink_cell__"


class ClaimLinkPreprocessor(ExecutePreprocessor):
    """Execute a notebook with the notebook path and cell id available to claims.

    Use it instead of ``--execute``::

        jupyter nbconvert --to notebook \\
            --Exporter.preprocessors=claimlink.nbconvert.ClaimLinkPreprocessor paper.ipynb
    """

    def preprocess_cell(self, cell, resources, index):
        self._check_assign_resources(resources)
        if self._is_python() and cell.get("cell_type") == "code":
            source = str(cell.get("source") or "")
            if source.strip():
                self._mark_cell(cell)
        return super().preprocess_cell(cell, resources, index)

    def _is_python(self):
        language = self.nb.metadata.get("language_info", {}).get("name")
        return language is None or language == "python"

    def _mark_cell(self, cell):
        metadata = self.resources.get("metadata") or {}
        name = metadata.get("name")
        path = metadata.get("path") or ""
        notebook = Path(path, f"{name}.ipynb").resolve() if name else None
        # --stdin has no file on disk; never invent a path for it.
        notebook_file = str(notebook) if notebook and notebook.is_file() else None
        marker = {"file": notebook_file, "cell_id": cell.get("id")}
        msg_id = self.kc.execute(
            f"{MARKER} = {marker!r}", silent=True, store_history=False
        )
        self.wait_for_reply(msg_id)
