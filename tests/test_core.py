"""Tests for the public claim() API and change detection."""

import builtins
import hashlib
import importlib.util
import inspect
import warnings
from pathlib import Path
from types import SimpleNamespace

import pytest

import claimlink
from claimlink import claim
from claimlink.errors import (
    ClaimLocationChangedWarning,
    ClaimLocationUnavailableWarning,
    ClaimValueChangedWarning,
    ClaimLockError,
)
from claimlink.storage import load, save

LOCK = "claim-lock.json"


@pytest.fixture(autouse=True)
def _isolated_project(tmp_path, monkeypatch):
    monkeypatch.delenv("CLAIMLINK_ROOT", raising=False)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _record(name, value, unit=None, description=None):
    """Register a claim from a fixed source line, recording any warnings."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        claim(name, value, unit=unit, description=description)
    return caught


def _of(caught, category):
    return [w for w in caught if issubclass(w.category, category)]


def _stored(**overrides):
    """Return a seeded lock-file record, with fields replaceable per test."""
    record = {
        "name": "seeded",
        "value": 1,
        "value_type": "int",
        "unit": None,
        "description": None,
        "location": {"type": "script", "file": "old.py", "line": 1},
        "created_at": "1999-01-01T00:00:00Z",
        "updated_at": "1999-01-01T00:00:00Z",
    }
    record.update(overrides)
    return record


def _load_module(path):
    spec = importlib.util.spec_from_file_location(f"claimlink_test_{path.stem}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_new_claim_writes_record_next_to_cwd(tmp_path):
    line = inspect.currentframe().f_lineno + 1
    claim("papers", 124, unit="papers", description="Total papers.")

    path = tmp_path / LOCK
    assert path.is_file()
    record = load(path)["claims"]["papers"]
    assert list(record) == [
        "name",
        "value",
        "value_type",
        "unit",
        "description",
        "location",
        "created_at",
        "updated_at",
    ]
    assert record["name"] == "papers"
    assert record["value"] == 124
    assert record["value_type"] == "int"
    assert record["unit"] == "papers"
    assert record["description"] == "Total papers."
    assert record["created_at"] == record["updated_at"]
    assert len(record["updated_at"]) == 20
    assert Path(record["location"]["file"]).as_posix().endswith("tests/test_core.py")
    assert record["location"]["line"] == line


@pytest.mark.parametrize(
    ("value", "expected_type"),
    [
        (0, "int"),
        (0.0, "float"),
        ("", "str"),
        (False, "bool"),
        (None, "null"),
        ([], "list"),
        ({}, "dict"),
    ],
)
def test_falsy_values_persist_without_false_change_warning(
    tmp_path, value, expected_type
):
    _record("falsy", value)
    caught = _record("falsy", value)

    assert not _of(caught, ClaimValueChangedWarning)
    record = load(tmp_path / LOCK)["claims"]["falsy"]
    assert record["value"] == value
    assert record["value_type"] == expected_type


def test_claims_merge_and_unrelated_records_are_preserved(tmp_path):
    untouched = {
        "name": "untouched",
        "value": 7,
        "value_type": "int",
        "unit": None,
        "description": None,
        "location": {"type": "script", "file": "old.py", "line": 1},
        "created_at": "1999-01-01T00:00:00Z",
        "updated_at": "1999-01-01T00:00:00Z",
    }
    save(tmp_path / LOCK, {"schema_version": 1, "claims": {"untouched": untouched}})

    _record("first", 1)
    _record("second", 2)

    claims = load(tmp_path / LOCK)["claims"]
    assert set(claims) == {"untouched", "first", "second"}
    assert claims["untouched"] == untouched


def test_claim_names_are_distinct_by_exact_text(tmp_path):
    for name in ("Papers", "papers", "papers "):
        assert _record(name, 1) == []

    assert len(load(tmp_path / LOCK)["claims"]) == 3


def test_same_value_keeps_created_at_and_refreshes_updated_at(tmp_path):
    _record("stable", 7)
    path = tmp_path / LOCK
    registry = load(path)
    registry["claims"]["stable"]["created_at"] = "2000-01-01T00:00:00Z"
    registry["claims"]["stable"]["updated_at"] = "2000-01-01T00:00:00Z"
    save(path, registry)

    caught = _record("stable", 7)

    assert caught == []
    record = load(path)["claims"]["stable"]
    assert record["created_at"] == "2000-01-01T00:00:00Z"
    assert record["updated_at"] != "2000-01-01T00:00:00Z"
    assert len(record["updated_at"]) == 20


def test_value_change_warns_with_exact_message(tmp_path):
    _record("papers", 124)
    caught = _record("papers", 130)

    warnings_found = _of(caught, ClaimValueChangedWarning)
    assert len(warnings_found) == 1
    assert str(warnings_found[0].message) == (
        "Claim 'papers' changed:\n"
        "  Previous value: 124\n"
        "  New value:      130\n\n"
        "The claim-lock.json file has been updated."
    )
    assert load(tmp_path / LOCK)["claims"]["papers"]["value"] == 130


@pytest.mark.parametrize(("first", "second"), [(True, 1), (1, 1.0)])
def test_type_only_change_warns(tmp_path, first, second):
    _record("typed", first)
    caught = _record("typed", second)

    assert len(_of(caught, ClaimValueChangedWarning)) == 1
    record = load(tmp_path / LOCK)["claims"]["typed"]
    assert record["value"] == second
    assert record["value_type"] == type(second).__name__


def test_missing_value_type_does_not_warn_on_unchanged_value(tmp_path):
    stored = _stored(name="legacy", value=5)
    stored.pop("value_type")
    save(tmp_path / LOCK, {"schema_version": 1, "claims": {"legacy": stored}})

    caught = _record("legacy", 5)

    assert not _of(caught, ClaimValueChangedWarning)
    assert load(tmp_path / LOCK)["claims"]["legacy"]["value_type"] == "int"


@pytest.mark.parametrize(
    ("first", "second"),
    [
        ({"unit": "s"}, {"unit": "ms"}),
        ({"description": "elapsed"}, {"description": "wall time"}),
    ],
    ids=["unit-only", "description-only"],
)
def test_single_metadata_change_is_silent_and_persisted(tmp_path, first, second):
    assert _record("measured", 1, **first) == []
    before = load(tmp_path / LOCK)["claims"]["measured"]

    caught = _record("measured", 1, **second)

    assert caught == []
    record = load(tmp_path / LOCK)["claims"]["measured"]
    expected = {**first, **second}
    assert record["unit"] == expected.get("unit")
    assert record["description"] == expected.get("description")
    assert record["value"] == before["value"] == 1
    assert record["created_at"] == before["created_at"]
    assert _record("measured", 1, **second) == []


def test_unit_and_description_can_be_reset_to_none(tmp_path):
    _record("measured", 1, unit="s", description="elapsed")
    caught = _record("measured", 1)

    assert caught == []
    record = load(tmp_path / LOCK)["claims"]["measured"]
    assert record["unit"] is None
    assert record["description"] is None


def test_location_change_warns_and_keeps_canonical_location(tmp_path):
    _record("shared", 1)
    canonical = load(tmp_path / LOCK)["claims"]["shared"]["location"]

    other = tmp_path / "other.py"
    other.write_text(
        "from claimlink import claim\n"
        "\n"
        "claim('shared', 2)\n",
        encoding="utf-8",
    )
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _load_module(other)

    warnings_found = _of(caught, ClaimLocationChangedWarning)
    assert len(warnings_found) == 1
    message = str(warnings_found[0].message)
    assert "shared" in message
    assert "other.py" in message
    assert "canonical location was kept" in message
    record = load(tmp_path / LOCK)["claims"]["shared"]
    assert record["location"] == canonical
    assert record["value"] == 2


def test_location_identity_includes_line(tmp_path):
    stored = {
        "name": "lined",
        "value": 1,
        "value_type": "int",
        "unit": None,
        "description": None,
        "location": {
            "type": "script",
            "file": Path(__file__).resolve().as_posix(),
            "line": 1,
        },
        "created_at": "1999-01-01T00:00:00Z",
        "updated_at": "1999-01-01T00:00:00Z",
    }
    save(tmp_path / LOCK, {"schema_version": 1, "claims": {"lined": stored}})

    caught = _record("lined", 1)

    assert len(_of(caught, ClaimLocationChangedWarning)) == 1
    record = load(tmp_path / LOCK)["claims"]["lined"]
    assert record["location"]["line"] == 1


@pytest.mark.parametrize("seeded", ["absent", None, "x.py:5", [1], {}, {"file": 3}])
def test_malformed_stored_location_is_silently_replaced(tmp_path, seeded):
    stored = _stored(name="mended")
    if seeded == "absent":
        stored.pop("location")
    else:
        stored["location"] = seeded
    save(tmp_path / LOCK, {"schema_version": 1, "claims": {"mended": stored}})

    caught = _record("mended", 1)

    assert not _of(caught, ClaimLocationChangedWarning)
    _record("fresh", 1)
    claims = load(tmp_path / LOCK)["claims"]
    assert claims["mended"]["location"] == claims["fresh"]["location"]


def test_stored_name_is_healed_to_the_claim_key(tmp_path):
    stored = _stored(name="Stale", location={"type": "x"})
    save(tmp_path / LOCK, {"schema_version": 1, "claims": {"papers": stored}})

    caught = _record("papers", 1)

    assert caught == []
    assert load(tmp_path / LOCK)["claims"]["papers"]["name"] == "papers"


def test_notebook_rerun_keeps_first_execution_count(monkeypatch, tmp_path):
    notebook = tmp_path / "nb.ipynb"

    class FakeShell:
        def __init__(self, prompt_count, code):
            self.user_ns = {"__session__": str(notebook)}
            self.parent_header = {
                "metadata": {"cellId": "cell-1"},
                "content": {"code": code},
            }
            self.displayhook = SimpleNamespace(prompt_count=prompt_count)

    sources = [
        "claim('accuracy', 0.9)\n",
        "claim('accuracy', 0.9)  # rerun\n",
    ]
    for prompt_count, source in zip((1, 2), sources):
        shell = FakeShell(prompt_count, source)
        monkeypatch.setattr(builtins, "get_ipython", lambda: shell, raising=False)
        namespace = {"claim": claim}
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            exec(compile(source, "<ipython-input-1-x>", "exec"), namespace)

    assert caught == []
    registry = load(tmp_path / LOCK)
    assert list(registry["claims"]) == ["accuracy"]
    record = registry["claims"]["accuracy"]
    assert record["value"] == 0.9
    assert record["location"]["type"] == "notebook"
    assert record["location"]["cell_id"] == "cell-1"
    assert record["location"]["execution_count"] == 1
    assert record["location"]["cell_source_hash"] == hashlib.sha256(
        sources[0].encode("utf-8")
    ).hexdigest()


def test_unavailable_notebook_metadata_warns_per_message(monkeypatch, tmp_path):
    class FakeShell:
        user_ns = {}
        parent_header = {}
        execution_count = None

    monkeypatch.setattr(builtins, "get_ipython", lambda: FakeShell(), raising=False)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        exec(
            compile("claim('nb', 1)\n", "<ipython-input-1-x>", "exec"),
            {"claim": claim},
        )

    messages = [str(w.message) for w in _of(caught, ClaimLocationUnavailableWarning)]
    assert messages == [
        "Claim 'nb': notebook filename is not available from this frontend.",
        "Claim 'nb': notebook cell id is not available from this frontend.",
    ]


def test_unsupported_value_raises_and_writes_nothing(tmp_path):
    with pytest.raises(TypeError):
        claim("bad", object())
    assert not (tmp_path / LOCK).exists()


@pytest.mark.parametrize(
    ("args", "kwargs", "exc", "fragment"),
    [
        ((123, 1), {}, TypeError, "int"),
        (("", 1), {}, ValueError, "empty"),
        (("   \t ", 1), {}, ValueError, "empty"),
        (("x", 1), {"unit": 5}, TypeError, "unit"),
        (("x", 1), {"description": []}, TypeError, "description"),
    ],
)
def test_invalid_arguments_leave_file_untouched(tmp_path, args, kwargs, exc, fragment):
    with pytest.raises(exc) as excinfo:
        claim(*args, **kwargs)
    assert fragment in str(excinfo.value)
    assert not (tmp_path / LOCK).exists()


@pytest.mark.parametrize("field", ["name", "unit", "description"])
def test_unpaired_surrogate_raises_and_writes_nothing(tmp_path, field):
    kwargs = {field: "bad\ud800"} if field != "name" else {}
    args = ("bad\ud800" if field == "name" else "ok", 1)

    with pytest.raises(ValueError) as excinfo:
        claim(*args, **kwargs)

    assert f"claim {field} is not valid UTF-8" in str(excinfo.value)
    assert not (tmp_path / LOCK).exists()


def test_claimlink_root_env_var_selects_project(tmp_path, monkeypatch):
    target = tmp_path / "project"
    monkeypatch.setenv("CLAIMLINK_ROOT", str(target))

    _record("rooted", 1)

    assert (target / LOCK).is_file()
    assert not (tmp_path / LOCK).exists()


def test_record_has_exactly_the_documented_fields(tmp_path):
    expected = [
        "name",
        "value",
        "value_type",
        "unit",
        "description",
        "location",
        "created_at",
        "updated_at",
    ]
    for _ in range(3):
        _record("stable", [1, {"a": 2}])

    record = load(tmp_path / LOCK)["claims"]["stable"]
    assert list(record) == expected
    assert "history" not in record


def test_malformed_lock_file_propagates_and_is_untouched(tmp_path):
    path = tmp_path / LOCK
    path.write_text("{not json", encoding="utf-8")

    with pytest.raises(ClaimLockError):
        claim("anything", 1)
    assert path.read_text(encoding="utf-8") == "{not json"


def test_public_import_is_the_core_function():
    assert claimlink.claim is claimlink.core.claim
    assert claim is claimlink.core.claim
    assert claimlink.__all__ == ["claim"]
