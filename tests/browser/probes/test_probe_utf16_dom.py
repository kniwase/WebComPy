"""``Text.splitText`` UTF-16 boundary contracts on the real DOM.

Contract: offsets count UTF-16 code units; splitting between the halves of a
surrogate pair leaves lone surrogates preserved in each half (mirroring
``FakeDOMNode.splitText``); splitting at pair-aligned offsets is clean;
out-of-range offsets raise an ``IndexSizeError``-named DOM exception.
"""


def _make_text(data):
    import js

    node = js.document.createTextNode(data)
    js.document.body.appendChild(node)
    return node


def test_splittext_ascii_boundary(app, dom_root):
    text = _make_text("abcdef")

    tail = text.splitText(2)

    assert str(text.data) == "ab"
    assert str(tail.data) == "cdef"


def test_splittext_at_pair_aligned_offset(app):
    text = _make_text("\U0001f600abc")

    tail = text.splitText(2)

    assert str(text.data) == "\U0001f600"
    assert str(tail.data) == "abc"


def test_splittext_mid_surrogate_preserves_lone_halves(app):
    """Splitting between high and low surrogates keeps each half intact.

    Observed on the pinned runtime and mirrored by ``FakeDOMNode.splitText``:
    UTF-16 units of ``"a😀b"`` are ``[a][high][low][b]``; splitting at offset
    2 (between the surrogate halves) yields head ``"a\\ud83d"`` (lone high)
    and tail ``"\\ude00b"`` (lone low + ``"b"``).
    """
    text = _make_text("a\U0001f600b")

    tail = text.splitText(2)

    assert str(text.data) == "a\ud83d"
    assert str(tail.data) == "\ude00b"


def test_splittext_mid_surrogate_at_pair_start(app):
    text = _make_text("\U0001f600ab")

    tail = text.splitText(1)

    assert str(text.data) == "\ud83d"
    assert str(tail.data) == "\ude00ab"


def test_splittext_offset_zero_returns_full_tail(app):
    text = _make_text("xyz")

    tail = text.splitText(0)

    assert str(text.data) == ""
    assert str(tail.data) == "xyz"


def test_splittext_out_of_range_raises_index_size_error(app):
    from pyodide.ffi import JsException

    text = _make_text("abc")

    raised = None
    try:
        text.splitText(99)
    except JsException as e:
        raised = e

    assert raised is not None
    assert raised.name == "IndexSizeError"
