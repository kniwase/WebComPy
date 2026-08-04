## ADDED Requirements

### Requirement: FakeDOMNode.splitText SHALL follow the DOM Text.splitText contract with UTF-16 offsets

`FakeDOMNode.splitText(offset)` SHALL split the receiver's text at the given offset interpreted as UTF-16 code units (the browser `Text.splitText` contract), truncating the receiver to the first `offset` code units, creating a new `FakeDOMNode("#text", ...)` holding the tail, inserting it into the parent's `childNodes` immediately after the receiver (appending when the receiver is last), and returning the new node. Splitting inside a surrogate pair SHALL produce lone-surrogate halves, mirroring browser behavior. `splitText` on a non-text node SHALL raise `TypeError`; an `offset` outside `[0, utf16_length]` SHALL raise `IndexError`.

#### Scenario: splitText splits at a UTF-16 code-unit boundary
- **WHEN** a `FakeDOMNode("#text", text_content="😀x")` is split at offset `2`
- **THEN** the receiver holds `"😀"` and the returned node holds `"x"`

#### Scenario: splitText inside a surrogate pair mirrors the browser
- **WHEN** a `FakeDOMNode("#text", text_content="😀x")` is split at offset `1`
- **THEN** the receiver holds the lone high surrogate and the returned node holds the lone low surrogate followed by `"x"`

#### Scenario: splitText raises on invalid input
- **WHEN** `splitText` is called on an element node, or with an offset outside the text length
- **THEN** `TypeError` (element node) or `IndexError` (offset) SHALL be raised
