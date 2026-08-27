# Delta: virtual-dom

## ADDED Requirements

### Requirement: ServerDOMPort shall resolve a documented CSS selector subset against the completed document tree

`ServerDOMPort.query_selector(selector)` SHALL resolve a CSS selector against the completed virtual document tree of its render context and return the first matching node in depth-first document order, or `None` when nothing matches. Resolution SHALL become available once the HTML assembly attaches the rendered document root to the port; before attachment, or in contexts without a server document tree (e.g. unit tests that construct ports standalone), `query_selector` SHALL return `None`. The supported selector subset SHALL be: type selectors, class selectors (`.name`), ID selectors (`#id`), their compounds (`div.class#id`), descendant combinators (whitespace), child combinators (`>`), and comma-separated groups. Any other syntax — attribute selectors, pseudo-classes/elements, universal-suffix edge constructs beyond this list — SHALL raise `ValueError`, which callers convert to the documented resolve-failure fallback. Resolution SHALL be read-only: it SHALL NOT mutate the tree. `get_element_by_id()` SHALL continue returning `None`.

#### Scenario: Id selector resolves against completed scaffold

- **WHEN** the assembled virtual document contains `<div id="footer-root">` outside the app subtree and `query_selector("#footer-root")` is called after assembly completes
- **THEN** the returned node SHALL be that div
- **AND** the node graph SHALL be unchanged by the query

#### Scenario: Descendant combinator matches in document order

- **WHEN** the document contains two elements matching `.menu-host`, one nested inside the other
- **THEN** `query_selector(".wrapper .menu-host")` SHALL return the node appearing first in depth-first document order among matches

#### Scenario: Child combinator restricts direct parentage

- **WHEN** an element `.a` has a direct child `.b` and a deeper descendant `.b`
- **THEN** `query_selector(".a > .b")` SHALL return only among nodes whose parent chain satisfies direct child relation, returning the first such match

#### Scenario: Unsupported syntax raises ValueError

- **WHEN** `query_selector("input[type=text]")` is called
- **THEN** a `ValueError` SHALL be raised
- **AND** no partial match SHALL be returned

#### Scenario: No attached document returns None

- **WHEN** `query_selector("body")` is called on a standalone `ServerDOMPort` with no assembled document
- **THEN** `None` SHALL be returned

#### Scenario: Comment nodes participate as boundary siblings only

- **WHEN** a query resolves over a subtree containing comment nodes between element children
- **THEN** comments SHALL never be returned as matches
- **AND** they SHALL NOT prevent matching of adjacent element children
