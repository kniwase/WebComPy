"""``to_js`` / ``is_none`` / ``undefined`` JS interop contracts.

Contracts codified as observed on the pinned runtime:

- ``pyodide.ffi.to_js`` converts dicts to plain JS objects (``Object``) by
  default; ``dict_converter=js.Object.fromEntries`` yields attribute access.
- ``is_none`` lives at ``pyscript.ffi.is_none`` (not ``pyodide.ffi``) and
  treats both ``None`` and ``js.undefined`` as none.
- JS ``undefined`` converts to Python ``None`` when it crosses the FFI
  boundary (``from js import undefined; undefined is None``).
"""


def test_to_js_dict_defaults_to_plain_object(app):
    from pyodide.ffi import to_js

    converted = to_js({"a": 1})

    assert converted.constructor.name == "Object"


def test_to_js_with_object_from_entries_makes_attributes(app):
    import js
    from pyodide.ffi import to_js

    converted = to_js({"a": 1, "b": "x"}, dict_converter=js.Object.fromEntries)

    assert converted.a == 1
    assert converted.b == "x"


def test_pyscript_ffi_is_none_treats_none_and_undefined_as_none(app):
    from js import undefined
    from pyscript import ffi

    assert ffi.is_none(None)
    assert ffi.is_none(undefined)


def test_pyscript_ffi_is_none_rejects_falsy_non_none_values(app):
    from pyscript import ffi

    assert not ffi.is_none(0)
    assert not ffi.is_none("")
    assert not ffi.is_none(False)


def test_undefined_converts_to_python_none_at_boundary(app):
    from js import undefined

    # Observed contract: the JS `undefined` value arrives as Python `None`.
    assert undefined is None


def test_scalar_roundtrip_through_js(app):
    import js

    assert int(js.Number(2)) == 2
    assert str(js.String("x")) == "x"
