"""Tests for claim-lock.json reading, writing and atomic replacement."""

import copy
import json
import os
import stat
import sys
from pathlib import Path

import pytest

from claimlink.errors import ClaimLockError
from claimlink.storage import (
    LOCK_FILENAME,
    SCHEMA_VERSION,
    load,
    lock_path,
    project_root,
    save,
)


def test_lock_path_joins_filename(tmp_path):
    assert lock_path(tmp_path) == tmp_path / "claim-lock.json"
    assert LOCK_FILENAME == "claim-lock.json"


def test_project_root_defaults_to_cwd(tmp_path, monkeypatch):
    monkeypatch.delenv("CLAIMLINK_ROOT", raising=False)
    monkeypatch.chdir(tmp_path)
    assert project_root() == Path.cwd() == tmp_path


def test_project_root_honours_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAIMLINK_ROOT", str(tmp_path / "sub" / ".."))
    assert project_root() == tmp_path.resolve()

    monkeypatch.setenv("CLAIMLINK_ROOT", "")
    monkeypatch.chdir(tmp_path)
    assert project_root() == Path.cwd()


def test_load_missing_file(tmp_path):
    assert load(tmp_path / LOCK_FILENAME) == {
        "schema_version": SCHEMA_VERSION,
        "claims": {},
    }


def test_load_defaults_schema_version(tmp_path):
    path = tmp_path / LOCK_FILENAME
    path.write_text('{"claims": {}}', encoding="utf-8")
    assert load(path) == {"schema_version": SCHEMA_VERSION, "claims": {}}


def test_round_trip_sorts_claims_and_formats_json(tmp_path):
    path = tmp_path / LOCK_FILENAME
    registry = {
        "schema_version": 1,
        "claims": {
            "zeta claim": {"value": 2},
            "alpha claim": {"value": 1},
        },
    }
    save(path, registry)

    raw = path.read_text(encoding="utf-8")
    assert raw.startswith('{\n  "')  # top-level keys are indented by two spaces
    assert '\n    "' in raw  # nested claims are indented further
    assert raw.index('"alpha claim"') < raw.index('"zeta claim"')
    assert raw.endswith("}\n")
    assert json.loads(raw) == registry
    assert list(load(path)["claims"]) == ["alpha claim", "zeta claim"]


def test_unicode_and_nested_values_round_trip(tmp_path):
    path = tmp_path / LOCK_FILENAME
    registry = {
        "schema_version": 1,
        "claims": {
            "größe": {"value": {"liste": ["ä", None, 1.5, True]}},
        },
    }
    save(path, registry)

    assert "ä" in path.read_text(encoding="utf-8")
    assert load(path) == registry


def test_record_fields_keep_their_order(tmp_path):
    path = tmp_path / LOCK_FILENAME
    save(path, {"schema_version": 1, "claims": {"a": {"z": 1, "a": 2}}})
    raw = path.read_text(encoding="utf-8")
    assert raw.index('"z"') < raw.index('"a": 2')


def test_extra_keys_and_unknown_fields_survive(tmp_path):
    path = tmp_path / LOCK_FILENAME
    registry = {
        "schema_version": 1,
        "future_key": {"kept": True},
        "claims": {"one": {"value": 1, "unknown_field": ["x"]}},
    }
    save(path, registry)
    assert load(path) == registry


def test_malformed_json_raises_claim_lock_error(tmp_path):
    path = tmp_path / LOCK_FILENAME
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(ClaimLockError) as excinfo:
        load(path)
    assert str(path) in str(excinfo.value)


@pytest.mark.parametrize(
    "content",
    [
        "[]",
        '{"claims": []}',
        '{"claims": {"bad record": "not an object"}}',
    ],
)
def test_wrong_shapes_raise_claim_lock_error(tmp_path, content):
    path = tmp_path / LOCK_FILENAME
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ClaimLockError) as excinfo:
        load(path)
    assert str(path) in str(excinfo.value)


@pytest.mark.parametrize(
    ("content", "key"),
    [
        ('{"schema_version": 1, "schema_version": 2, "claims": {}}', "schema_version"),
        ('{"claims": {"a": {"v": 1}, "a": {"v": 2}}}', "a"),
        ('{"claims": {"a": {"v": 1, "v": 2}}}', "v"),
    ],
)
def test_duplicate_keys_raise_claim_lock_error(tmp_path, content, key):
    path = tmp_path / LOCK_FILENAME
    path.write_text(content, encoding="utf-8")
    original = path.read_bytes()
    with pytest.raises(ClaimLockError) as excinfo:
        load(path)
    assert key in str(excinfo.value)
    assert str(path) in str(excinfo.value)
    assert path.read_bytes() == original


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_non_finite_json_constant_raises_claim_lock_error(tmp_path, constant):
    path = tmp_path / LOCK_FILENAME
    path.write_text(
        '{"claims": {"a": {"value": ' + constant + "}}}", encoding="utf-8"
    )
    with pytest.raises(ClaimLockError) as excinfo:
        load(path)
    assert str(path) in str(excinfo.value)
    assert "non-finite" in str(excinfo.value)


def test_non_utf8_file_raises_claim_lock_error(tmp_path):
    path = tmp_path / LOCK_FILENAME
    path.write_bytes('{"claims": {"größe": {}}}'.encode("latin-1"))
    with pytest.raises(ClaimLockError) as excinfo:
        load(path)
    assert str(path) in str(excinfo.value)


def test_huge_integer_raises_claim_lock_error(tmp_path):
    if not hasattr(sys, "get_int_max_str_digits"):
        pytest.skip("int-to-str digit limit is 3.11+ only")
    path = tmp_path / LOCK_FILENAME
    path.write_text('{"claims": {"a": {"v": ' + "9" * 5000 + "}}}", encoding="utf-8")
    with pytest.raises(ClaimLockError) as excinfo:
        load(path)
    assert str(path) in str(excinfo.value)


def test_bom_is_ignored_on_load_and_not_written_on_save(tmp_path):
    path = tmp_path / LOCK_FILENAME
    path.write_bytes(b"\xef\xbb\xbf" + b'{"claims": {"a": {}}}')
    assert load(path)["claims"] == {"a": {}}
    save(path, load(path))
    assert not path.read_bytes().startswith(b"\xef\xbb\xbf")


@pytest.mark.parametrize(
    "registry",
    [
        {"schema_version": 1, "claims": {"b": {"value": 2}, "a": {"value": 1}}},
        {"schema_version": 1},
    ],
)
def test_save_does_not_mutate_registry(tmp_path, registry):
    path = tmp_path / LOCK_FILENAME
    before = copy.deepcopy(registry)
    save(path, registry)
    assert registry == before
    assert list(registry) == list(before)


def test_save_sets_owner_and_group_readable_mode_on_new_file(tmp_path):
    if os.name == "nt":
        pytest.skip("POSIX file modes only")
    path = tmp_path / LOCK_FILENAME
    save(path, {"schema_version": 1, "claims": {}})
    assert stat.S_IMODE(path.stat().st_mode) == 0o644


def test_save_preserves_existing_file_mode(tmp_path):
    if os.name == "nt":
        pytest.skip("POSIX file modes only")
    path = tmp_path / LOCK_FILENAME
    path.write_text('{"schema_version": 1, "claims": {}}', encoding="utf-8")
    os.chmod(path, 0o640)
    save(path, {"schema_version": 1, "claims": {}})
    assert stat.S_IMODE(path.stat().st_mode) == 0o640


def test_save_creates_missing_parents(tmp_path):
    path = tmp_path / "nested" / "deeper" / LOCK_FILENAME
    save(path, {"schema_version": 1, "claims": {}})
    assert load(path) == {"schema_version": 1, "claims": {}}


def test_failed_replace_preserves_original(tmp_path, monkeypatch):
    path = tmp_path / LOCK_FILENAME
    save(path, {"schema_version": 1, "claims": {"a": {"value": 1}}})
    original = path.read_bytes()

    def fail(src, dst):
        raise OSError("simulated replace failure")

    monkeypatch.setattr(os, "replace", fail)
    with pytest.raises(OSError):
        save(path, {"schema_version": 1, "claims": {"a": {"value": 2}}})

    assert path.read_bytes() == original
    assert [p.name for p in tmp_path.iterdir() if p.name != LOCK_FILENAME] == []


def test_successful_save_leaves_no_temp_file(tmp_path):
    path = tmp_path / LOCK_FILENAME
    save(path, {"schema_version": 1, "claims": {}})
    assert sorted(p.name for p in tmp_path.iterdir()) == [LOCK_FILENAME]


def test_save_fsyncs_before_replacing(tmp_path, monkeypatch):
    calls = []
    real_fsync = os.fsync

    def recording_fsync(fd):
        calls.append(fd)
        return real_fsync(fd)

    monkeypatch.setattr(os, "fsync", recording_fsync)
    save(tmp_path / LOCK_FILENAME, {"schema_version": 1, "claims": {}})
    assert calls
