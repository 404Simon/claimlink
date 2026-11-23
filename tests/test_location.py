import builtins
import hashlib
import importlib.util
import inspect
from pathlib import Path
from types import SimpleNamespace

import pytest

from claimlink.location import detect_location


class FakeShell:
    def __init__(
        self,
        *,
        user_ns=None,
        parent_header=None,
        execution_count=None,
        prompt_count=None,
        filename_map=None,
    ):
        self.user_ns = {} if user_ns is None else user_ns
        self.parent_header = {} if parent_header is None else parent_header
        self.execution_count = execution_count
        if prompt_count is not None:
            self.displayhook = SimpleNamespace(prompt_count=prompt_count)
        if filename_map is not None:
            self.compile = SimpleNamespace(_filename_map=filename_map)


@pytest.fixture(autouse=True)
def _clear_jupyter_env(monkeypatch):
    monkeypatch.delenv("JPY_SESSION_NAME", raising=False)


def _load_script(path):
    spec = importlib.util.spec_from_file_location(f"claimlink_test_{path.stem}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _exec_cell(source, root):
    namespace = {"detect_location": detect_location, "root": root}
    exec(compile(source, "<ipython-input-7-test>", "exec"), namespace)
    return namespace["result"]


def test_script_location(tmp_path):
    script = tmp_path / "script.py"
    script.write_text(
        "from claimlink.location import detect_location\n"
        "\n"
        "def run(root):\n"
        "    return detect_location(root)\n"
    )

    location, messages = _load_script(script).run(tmp_path)

    assert location == {"type": "script", "file": "script.py", "line": 4}
    assert messages == []


def test_nested_calls_report_declaration_line(tmp_path):
    script = tmp_path / "nested.py"
    script.write_text(
        "from claimlink.location import detect_location\n"
        "\n"
        "def inner(root):\n"
        "    return detect_location(root)\n"
        "\n"
        "def outer(root):\n"
        "    return inner(root)\n"
    )

    location, messages = _load_script(script).outer(tmp_path)

    assert location == {"type": "script", "file": "nested.py", "line": 4}
    assert messages == []


def test_closure_reports_call_line(tmp_path):
    script = tmp_path / "closure.py"
    script.write_text(
        "from claimlink.location import detect_location\n"
        "\n"
        "def make(root):\n"
        "    def probe():\n"
        "        return detect_location(root)\n"
        "    return probe()\n"
    )

    location, messages = _load_script(script).make(tmp_path)

    assert location == {"type": "script", "file": "closure.py", "line": 5}
    assert messages == []


def test_file_outside_project_root_is_absolute(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    script = outside / "analysis.py"
    script.write_text(
        "from claimlink.location import detect_location\n"
        "\n"
        "def run(root):\n"
        "    return detect_location(root)\n"
    )

    location, messages = _load_script(script).run(root)

    assert location == {"type": "script", "file": script.resolve().as_posix(), "line": 4}
    assert messages == []


def test_notebook_location_from_ipython(monkeypatch, tmp_path):
    notebook = tmp_path / "evaluation.ipynb"
    cell_source = "result = detect_location(root)\n"
    shell = FakeShell(
        user_ns={"__session__": str(notebook)},
        parent_header={"metadata": {"cellId": "cell-abc"}, "content": {"code": cell_source}},
        prompt_count=12,
    )
    monkeypatch.setattr(builtins, "get_ipython", lambda: shell, raising=False)

    location, messages = _exec_cell(cell_source, tmp_path)

    assert location["type"] == "notebook"
    assert location["file"] == "evaluation.ipynb"
    assert location["cell_id"] == "cell-abc"
    assert location["execution_count"] == 12
    assert location["line"] == 1
    assert location["cell_source_hash"] == hashlib.sha256(cell_source.encode("utf-8")).hexdigest()
    assert len(location["cell_source_hash"]) == 64
    assert messages == []


def test_execution_count_prefers_displayhook_prompt_count(monkeypatch, tmp_path):
    shell = FakeShell(
        user_ns={"__session__": str(tmp_path / "nb.ipynb")},
        parent_header={"metadata": {"cellId": "cell-1"}},
        execution_count=43,
        prompt_count=5,
    )
    monkeypatch.setattr(builtins, "get_ipython", lambda: shell, raising=False)

    location, messages = _exec_cell("result = detect_location(root)\n", tmp_path)

    assert location["execution_count"] == 5
    assert messages == []


def test_execution_count_without_displayhook_is_none(monkeypatch, tmp_path):
    shell = FakeShell(
        user_ns={"__session__": str(tmp_path / "nb.ipynb")},
        parent_header={"metadata": {"cellId": "cell-1"}},
        execution_count=43,
    )
    monkeypatch.setattr(builtins, "get_ipython", lambda: shell, raising=False)

    location, _ = _exec_cell("result = detect_location(root)\n", tmp_path)

    assert location["execution_count"] is None


def test_silent_run_has_no_execution_count(monkeypatch, tmp_path):
    cell_source = "result = detect_location(root)\n"
    shell = FakeShell(
        user_ns={"__session__": str(tmp_path / "nb.ipynb")},
        parent_header={
            "metadata": {"cellId": "cell-silent"},
            "content": {"code": cell_source, "store_history": False},
        },
        prompt_count=7,
    )
    monkeypatch.setattr(builtins, "get_ipython", lambda: shell, raising=False)

    location, _ = _exec_cell(cell_source, tmp_path)

    assert location["execution_count"] is None
    assert location["cell_id"] == "cell-silent"
    assert location["cell_source_hash"] == hashlib.sha256(cell_source.encode("utf-8")).hexdigest()


def test_declaration_in_same_cell_keeps_metadata(monkeypatch, tmp_path):
    shell = FakeShell(
        user_ns={"__session__": str(tmp_path / "nb.ipynb")},
        parent_header={"metadata": {"cellId": "cell-7"}, "content": {"code": "helper()\n"}},
        prompt_count=7,
        filename_map={"<ipython-input-7-test>": 7},
    )
    monkeypatch.setattr(builtins, "get_ipython", lambda: shell, raising=False)

    location, messages = _exec_cell("result = detect_location(root)\n", tmp_path)

    assert location["cell_id"] == "cell-7"
    assert location["execution_count"] == 7
    assert location["cell_source_hash"] is not None
    assert messages == []


def test_declaration_in_other_cell_is_not_attributed(monkeypatch, tmp_path):
    shell = FakeShell(
        user_ns={"__session__": str(tmp_path / "nb.ipynb")},
        parent_header={"metadata": {"cellId": "cell-other"}, "content": {"code": "helper()\n"}},
        prompt_count=7,
        filename_map={"<ipython-input-7-test>": 2, "<ipython-input-7-exec>": 7},
    )
    monkeypatch.setattr(builtins, "get_ipython", lambda: shell, raising=False)

    location, messages = _exec_cell("result = detect_location(root)\n", tmp_path)

    assert location["cell_id"] is None
    assert location["execution_count"] is None
    assert location["cell_source_hash"] is None
    assert len(messages) == 1
    assert "different notebook cell" in messages[0]


def test_nested_compile_off_by_one_keeps_metadata(monkeypatch, tmp_path):
    # %%capture-style nested compile is cached after the count increments, so
    # the mapped number is prompt_count + 1 but its filename is the last key.
    shell = FakeShell(
        user_ns={"__session__": str(tmp_path / "nb.ipynb")},
        parent_header={"metadata": {"cellId": "cell-nested"}, "content": {"code": "helper()\n"}},
        prompt_count=7,
        filename_map={"<ipython-input-7-exec>": 7, "<ipython-input-7-test>": 8},
    )
    monkeypatch.setattr(builtins, "get_ipython", lambda: shell, raising=False)

    location, messages = _exec_cell("result = detect_location(root)\n", tmp_path)

    assert location["cell_id"] == "cell-nested"
    assert location["execution_count"] == 7
    assert location["cell_source_hash"] is not None
    assert messages == []


def test_nested_run_cell_keeps_metadata(monkeypatch, tmp_path):
    # %%rerun-style nested run_cell caches a second compile (mapped 8) after the
    # executing cell's own compile (mapped 7), so the executing key is not last.
    shell = FakeShell(
        user_ns={"__session__": str(tmp_path / "nb.ipynb")},
        parent_header={"metadata": {"cellId": "cell-rerun"}, "content": {"code": "helper()\n"}},
        prompt_count=7,
        filename_map={"<ipython-input-7-test>": 7, "<ipython-input-7-exec>": 8},
    )
    monkeypatch.setattr(builtins, "get_ipython", lambda: shell, raising=False)

    location, messages = _exec_cell("result = detect_location(root)\n", tmp_path)

    assert location["cell_id"] == "cell-rerun"
    assert location["execution_count"] == 7
    assert location["cell_source_hash"] is not None
    assert messages == []


def test_duplicate_map_values_use_insertion_order(monkeypatch, tmp_path):
    shell = FakeShell(
        user_ns={"__session__": str(tmp_path / "nb.ipynb")},
        parent_header={"metadata": {"cellId": "cell-dup"}, "content": {"code": "helper()\n"}},
        prompt_count=7,
        filename_map={"<ipython-input-7-test>": 7, "<ipython-input-7-exec>": 7},
    )
    monkeypatch.setattr(builtins, "get_ipython", lambda: shell, raising=False)

    location, messages = _exec_cell("result = detect_location(root)\n", tmp_path)

    assert location["cell_id"] is None
    assert location["execution_count"] is None
    assert location["cell_source_hash"] is None
    assert len(messages) == 1
    assert "different notebook cell" in messages[0]


def test_silent_run_with_store_history_has_no_execution_count(monkeypatch, tmp_path):
    cell_source = "result = detect_location(root)\n"
    shell = FakeShell(
        user_ns={"__session__": str(tmp_path / "nb.ipynb")},
        parent_header={
            "metadata": {"cellId": "cell-silent-store"},
            "content": {"code": cell_source, "store_history": True, "silent": True},
        },
        prompt_count=7,
    )
    monkeypatch.setattr(builtins, "get_ipython", lambda: shell, raising=False)

    location, messages = _exec_cell(cell_source, tmp_path)

    assert location["execution_count"] is None
    assert location["cell_id"] == "cell-silent-store"
    assert location["cell_source_hash"] == hashlib.sha256(cell_source.encode("utf-8")).hexdigest()
    assert messages == []


def test_pseudo_filename_keeps_executing_cell_metadata(monkeypatch, tmp_path):
    shell = FakeShell(
        user_ns={"__session__": str(tmp_path / "nb.ipynb")},
        parent_header={"metadata": {"cellId": "cell-timed"}, "content": {"code": "helper()\n"}},
        prompt_count=7,
        filename_map={"<ipython-input-7-exec>": 7},
    )
    monkeypatch.setattr(builtins, "get_ipython", lambda: shell, raising=False)
    source = "result = detect_location(root)\n"
    namespace = {"detect_location": detect_location, "root": tmp_path}

    exec(compile(source, "<timed exec>", "exec"), namespace)

    location, messages = namespace["result"]
    assert location["cell_id"] == "cell-timed"
    assert location["execution_count"] == 7
    assert location["cell_source_hash"] is not None
    assert messages == []


def test_notebook_file_from_vscode_global(monkeypatch, tmp_path):
    notebook = tmp_path / "vscode.ipynb"
    shell = FakeShell(
        user_ns={"__vsc_ipynb_file__": str(notebook)},
        parent_header={"metadata": {"cellId": "cell-vsc"}},
        prompt_count=3,
    )
    monkeypatch.setattr(builtins, "get_ipython", lambda: shell, raising=False)

    location, _ = _exec_cell("result = detect_location(root)\n", tmp_path)

    assert location["file"] == "vscode.ipynb"


def test_notebook_file_from_environment(monkeypatch, tmp_path):
    notebook = tmp_path / "env.ipynb"
    monkeypatch.setenv("JPY_SESSION_NAME", str(notebook))
    shell = FakeShell(parent_header={"metadata": {"cellId": "cell-env"}}, prompt_count=1)
    monkeypatch.setattr(builtins, "get_ipython", lambda: shell, raising=False)

    location, messages = _exec_cell("result = detect_location(root)\n", tmp_path)

    assert location["file"] == "env.ipynb"
    assert messages == []


def test_notebook_file_expands_tilde(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("JPY_SESSION_NAME", raising=False)
    shell = FakeShell(
        user_ns={"__session__": "~/nb.ipynb"},
        parent_header={"metadata": {"cellId": "cell-tilde"}},
        prompt_count=1,
    )
    monkeypatch.setattr(builtins, "get_ipython", lambda: shell, raising=False)
    root = tmp_path / "project"

    location, messages = _exec_cell("result = detect_location(root)\n", root)

    assert location["file"] == (tmp_path / "nb.ipynb").resolve().as_posix()
    assert location["file"].startswith(str(tmp_path.resolve()))
    assert messages == []


def test_missing_notebook_filename(monkeypatch, tmp_path):
    shell = FakeShell(parent_header={"metadata": {"cellId": "cell-1"}}, prompt_count=1)
    monkeypatch.setattr(builtins, "get_ipython", lambda: shell, raising=False)

    location, messages = _exec_cell("result = detect_location(root)\n", tmp_path)

    assert location["file"] is None
    assert any("filename" in message for message in messages)


def test_missing_cell_id(monkeypatch, tmp_path):
    shell = FakeShell(
        user_ns={"__session__": str(tmp_path / "nb.ipynb")},
        parent_header={},
        prompt_count=1,
    )
    monkeypatch.setattr(builtins, "get_ipython", lambda: shell, raising=False)

    location, messages = _exec_cell("result = detect_location(root)\n", tmp_path)

    assert location["cell_id"] is None
    assert any("cell id" in message for message in messages)


def test_empty_shell_metadata_does_not_crash(monkeypatch, tmp_path):
    shell = FakeShell(user_ns={}, parent_header={}, execution_count=None)
    monkeypatch.setattr(builtins, "get_ipython", lambda: shell, raising=False)

    location, messages = _exec_cell("result = detect_location(root)\n", tmp_path)

    assert location["type"] == "notebook"
    assert location["file"] is None
    assert location["cell_id"] is None
    assert location["cell_source_hash"] is None
    assert len(messages) == 2


def test_embedded_nul_filename_does_not_raise(monkeypatch, tmp_path):
    monkeypatch.delattr(builtins, "get_ipython", raising=False)
    code = compile("result = detect_location(root)\n", "<cell>", "exec").replace(
        co_filename="\x00bad"
    )
    namespace = {"detect_location": detect_location, "root": tmp_path}

    exec(code, namespace)

    location, messages = namespace["result"]
    assert location["file"] is None
    assert messages == ["source file is not available"]


def test_pseudo_file_without_ipython(monkeypatch, tmp_path):
    monkeypatch.delattr(builtins, "get_ipython", raising=False)

    location, messages = _exec_cell("result = detect_location(root)\n", tmp_path)

    assert location == {"type": "script", "file": None, "line": 1}
    assert messages == ["source file is not available"]


def test_reports_test_file_not_package_internals():
    project_root = Path(__file__).resolve().parents[1]
    expected_line = inspect.currentframe().f_lineno + 1
    location, messages = detect_location(project_root)

    assert location == {"type": "script", "file": "tests/test_location.py", "line": expected_line}
    assert messages == []
