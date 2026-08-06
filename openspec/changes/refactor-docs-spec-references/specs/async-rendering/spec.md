## ADDED Requirements

### Requirement: _reposition_node() shall use is-None guards for node cache and parent

`_reposition_node()` SHALL guard its node-cache access with a strict is-None check (`if node is None: return`) before reading `node.parentNode`, and SHALL guard the resolved parent with `if parent is None or not parent:` (strict is-None check followed by truthiness) before re-inserting the node. This mirrors the `_get_node()` strict is-None contract: stale PyScript PyProxy objects can evaluate as falsy even when wrapping valid DOM nodes, so a bare truthiness check on the parent would skip a necessary re-insertion.

#### Scenario: PyProxy parent evaluates falsy

- **WHEN** `_reposition_node()` resolves a parent PyProxy that wraps a valid DOM node but evaluates as falsy in a boolean context
- **THEN** the strict is-None guard SHALL accept the parent and SHALL insert the node at the target index