import enum
import json
import math
import sys

import pytest

from claimlink.serialization import canonical, normalize, value_type


@pytest.mark.parametrize(
    ("value", "expected_type"),
    [
        (None, "null"),
        (True, "bool"),
        (False, "bool"),
        (7, "int"),
        (1.5, "float"),
        ("claim", "str"),
        ([1, 2], "list"),
        ({"a": 1}, "dict"),
    ],
)
def test_supported_values_round_trip(value, expected_type):
    normalized = normalize(value)
    assert normalized == value
    assert value_type(normalized) == expected_type


def test_nested_normalization_is_json_compatible():
    value = {"b": [1, {"c": None}], "a": 2.5}
    normalized = normalize(value)
    assert normalized == value
    assert normalized is not value
    assert json.loads(json.dumps(normalized)) == value


def test_shared_container_is_not_a_cycle():
    shared = [1]
    assert normalize([shared, shared]) == [[1], [1]]


def test_canonical_ignores_dict_order():
    assert canonical({"a": 1, "b": [2, 3]}) == canonical({"b": [2, 3], "a": 1})


def test_bool_and_int_are_distinct():
    assert value_type(True) == "bool"
    assert value_type(1) == "int"
    assert canonical([True]) != canonical([1])


def test_int_and_float_are_distinct():
    assert value_type(1) == "int"
    assert value_type(1.0) == "float"


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_non_finite_float_rejected(value):
    with pytest.raises(ValueError) as excinfo:
        normalize(value)
    assert "non-finite" in str(excinfo.value)
    assert repr(value) in str(excinfo.value)


@pytest.mark.parametrize("value", [object(), {1, 2}, (1, 2), b"bytes"])
def test_unsupported_type_rejected(value):
    with pytest.raises(TypeError, match=type(value).__name__):
        normalize(value)


def test_non_string_dict_key_rejected():
    with pytest.raises(TypeError) as excinfo:
        normalize({1: "one"})
    assert "string keys" in str(excinfo.value)
    assert "int" in str(excinfo.value)


def test_circular_list_rejected():
    value = []
    value.append(value)
    with pytest.raises(ValueError, match="circular"):
        normalize(value)


def test_circular_dict_rejected():
    value = {}
    value["self"] = value
    with pytest.raises(ValueError, match="circular"):
        normalize(value)


class _FakeNumpyScalar:
    ndim = 0

    def item(self):
        return 2.5


_FakeNumpyScalar.__module__ = "numpy"


class _FakeNumpyArray:
    ndim = 1


_FakeNumpyArray.__module__ = "numpy"


def test_fake_numpy_scalar_converted():
    normalized = normalize(_FakeNumpyScalar())
    assert normalized == 2.5
    assert type(normalized) is float
    assert value_type(normalized) == "float"


def test_fake_numpy_array_rejected():
    with pytest.raises(TypeError, match="scalar numpy"):
        normalize(_FakeNumpyArray())


def test_value_type_null_and_rejects_non_normalized():
    assert value_type(None) == "null"
    with pytest.raises(TypeError, match="set"):
        value_type({1, 2})


def test_canonical_format_is_pinned():
    assert canonical({"b": 1, "a": "é"}) == '{"a":"é","b":1}'


def test_unpaired_surrogate_rejected():
    with pytest.raises(ValueError, match="unpaired surrogate"):
        normalize("\ud800")


@pytest.mark.parametrize("value", [{"\ud800": 1}, {"outer": {"\ud800": 1}}])
def test_unpaired_surrogate_dict_key_rejected(value):
    with pytest.raises(ValueError, match="unpaired surrogate"):
        normalize(value)


class _Color(enum.IntEnum):
    RED = 1


class _Str(str):
    pass


class _Float(float):
    pass


class _ColorEnum(str, enum.Enum):
    RED = "red"


class _OverridingInt(int):
    def __int__(self):
        return 999


class _OverridingStr(str):
    def __str__(self):
        return "overridden"


class _OverridingFloat(float):
    def __float__(self):
        return 999.0


def test_subclasses_become_exact_builtins():
    cases = [(_Color.RED, int), (_Str("x"), str), (_Float(1.5), float)]
    for raw, expected in cases:
        normalized = normalize(raw)
        assert type(normalized) is expected
        assert normalized == raw


def test_overridden_conversion_hooks_do_not_change_the_value():
    assert normalize(_OverridingInt(7)) == 7
    assert normalize(_OverridingStr("real")) == "real"
    assert normalize(_OverridingFloat(1.5)) == 1.5


def test_str_enum_keeps_its_value():
    normalized = normalize(_ColorEnum.RED)
    assert normalized == "red"
    assert type(normalized) is str


class _ReversedKey(str):
    def __lt__(self, other):
        return str(self) > str(other)


def test_str_subclass_key_sorts_like_plain_str():
    normalized = normalize({_ReversedKey("a"): 1, _ReversedKey("b"): 2})
    assert all(type(key) is str for key in normalized)
    assert canonical(normalized) == canonical({"a": 1, "b": 2})


def test_int_enum_is_not_confused_with_bool():
    normalized = normalize(_Color.RED)
    assert type(normalized) is int
    assert value_type(normalized) == "int"
    assert canonical([normalized]) == canonical([1])


def test_deeply_nested_value_rejected():
    value = []
    # exceed the interpreter recursion limit regardless of how many frames
    # each level costs
    for _ in range(sys.getrecursionlimit() + 100):
        value = [value]
    with pytest.raises(ValueError, match="nested too deeply"):
        normalize(value)


class _SelfContainingNumpyScalar:
    ndim = 0

    def __init__(self):
        self._payload = [self]

    def item(self):
        return self._payload


_SelfContainingNumpyScalar.__module__ = "numpy"


def test_self_containing_numpy_scalar_rejected():
    with pytest.raises(ValueError, match="nested too deeply|circular"):
        normalize(_SelfContainingNumpyScalar())

