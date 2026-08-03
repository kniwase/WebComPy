## ADDED Requirements

### Requirement: Hydration SHALL normalize parser-merged text nodes to element-tree granularity before index-based adoption

`ElementWithChildren._hydrate_node()` SHALL NOT assume a pristine 1:1 correspondence between the element tree's child nodes and the browser DOM's `childNodes`. The HTML parser merges adjacent `#text` nodes during parsing, so a sequence of consecutive `TextElement` children (e.g. whitespace and interpolation holes adjacent in a composite body) can correspond to a single merged DOM `#text` node. Before per-child adoption proceeds by `_node_idx`, hydration SHALL detect a consecutive run of `TextElement` children whose combined expected text length is less than or equal to the DOM text present at the current sibling position, and SHALL split the merged DOM `#text` node via `splitText(offset)` at the cumulative expected-text boundary of each child in the run, so that each element-tree child once again has a distinct DOM node at its `_node_idx`.

Normalization SHALL be idempotent: when the DOM already has a 1:1 correspondence (no merging occurred, or splitting has already been applied), no further split SHALL be performed. Normalization SHALL apply only to the hydration path (`_hydrate_node`); server-side rendering, `_render`, refresh, reconcile, and positioning code SHALL remain unchanged. When the merged DOM text content does not equal the concatenation of the run's expected text contents, hydration SHALL fall back to the existing create/adopt fallback for the affected run rather than producing a misaligned split.

This requirement applies to `ElementWithChildren._hydrate_node` (regular containers indexing from base `0`) and to dynamic-container hydration paths (`DynamicElement._hydrate_node`, `RepeatElement`, `FragmentElement`) that rely on the same index-based `childNodes` adoption. A `NewLine` (`<br>`) or `RawHTML` (wrapper element) child renders a non-`#text` DOM node and SHALL terminate a text run; only consecutive `TextElement` children participate in a run.

#### Scenario: Hydrating a fragment body with merged adjacent text
- **WHEN** a keyed loop item's body is a fragment containing `<span>` + a `TextElement` + another `TextElement`, and the browser parser has merged the two `#text` nodes into one
- **THEN** `_hydrate_node` SHALL split the merged DOM `#text` node at the cumulative expected-text boundary so each `TextElement` adopts its own `#text` node at the correct `_node_idx`
- **AND** subsequent reconcile/positioning SHALL observe a 1:1 element-to-DOM correspondence

#### Scenario: No merge leaves the DOM untouched
- **WHEN** hydration encounters children whose DOM `childNodes` already correspond 1:1 to the element tree (no adjacent text was merged)
- **THEN** `_hydrate_node` SHALL perform no `splitText` calls
- **AND** adoption SHALL proceed exactly as before this change

#### Scenario: Content mismatch falls back rather than mis-splitting
- **WHEN** the merged DOM `#text` content does not equal the concatenation of a text run's expected contents (e.g. unexpected prerendered content)
- **THEN** hydration SHALL skip splitting that run and fall back to the existing per-node create/adopt behavior
- **AND** no exception SHALL propagate to the caller

#### Scenario: Keyed ReactiveDict loop hydrates with a composite item body
- **WHEN** a `ReactiveDict` keyed loop renders items whose body contains multiple elements interleaved with text, and the prerendered HTML is parsed by the browser
- **THEN** hydration SHALL normalize the merged text nodes for every item
- **AND** a subsequent mutation that reorders keys SHALL reconcile children to the correct DOM positions without empty nodes or leftover prerendered nodes
