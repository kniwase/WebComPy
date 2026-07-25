# Delta Spec: template-engine

## ADDED Requirements

### Requirement: Template expression language limitations shall be documented

The template expression grammar SHALL remain limited to identifiers with dot-notation paths. Subscripts (`items[0]`), calls (`user.name()`), filters (`x | upper`), comparisons (`a > b`), negation (`not a`), and containment (`x in y`) are NOT supported and SHALL raise `WebComPyException` where detectable. Dot-notation SHALL NOT traverse into `Signal`-held intermediate objects (only the final segment unwraps Signals). These are intentional design constraints, not defects.

#### Scenario: Unsupported syntax errors, not silent output
- **WHEN** a template uses `{{ items[0] }}` or `{% if a > b %}`
- **THEN** a descriptive `WebComPyException` SHALL be raised (per the error-quality requirement)
- **AND** the framework documentation SHALL list these constructs as unsupported

#### Scenario: Signal mid-path not traversed
- **WHEN** `{{ t.primary }}` is used with `t` being a `Signal` holding an object
- **THEN** resolution SHALL fail (the framework does not auto-unwrap intermediate Signals)
- **AND** the recommended pattern SHALL be passing the unwrapped value or a `Computed` in the context

### Requirement: For-loop semantics limitations shall be documented

One-variable iteration over a dict (`{% for v in my_dict %}`) SHALL iterate **values** (not keys, matching the `repeat()` overload contract). Two-variable unpacking SHALL be supported only for dict iterables. Loop metadata (`loop.index`, `loop.first`), `{% else %}` on for, `break`/`continue`, and iteration over `list[tuple]` with unpacking are NOT supported.

#### Scenario: Dict value iteration is the contract
- **WHEN** `{% for v in my_dict %}` is used with a dict or `ReactiveDict`
- **THEN** `v` SHALL bind to each value (this SHALL be documented as intentional, differing from Python's key iteration)

### Requirement: Scoped-CSS limitations shall be documented

Selectors targeting `:root`, `html`, or `body` in `scoped_style`/`css_text` SHALL be documented as dead rules (the cid attribute exists only on component elements). Duplicate selectors/properties/at-rule keys in `css_text` source SHALL be documented as last-wins. Statement at-rules (`@import`, `@charset`) SHALL be documented as dropped. Keyframe names SHALL be documented as global (same-named `@keyframes` in different components collide).

#### Scenario: :root rule documented as inert
- **WHEN** a developer writes `:root { --x: 1; }` in scoped CSS
- **THEN** the rule SHALL be emitted scoped (`:root[cid]`, matching nothing)
- **AND** this behavior SHALL be documented with the recommendation to use app-level styles (`app.style`) instead

### Requirement: HTML parsing limitations shall be documented

SVG/MathML foreign content SHALL be documented as unsupported (tag/attribute case is lowercased, breaking case-sensitive SVG names like `viewBox`/`linearGradient`). `textwrap.dedent` SHALL be documented as interacting destructively with intentional indentation inside `<pre>` in triple-quoted templates. `{# #}` template comments and literal-`{{` escaping SHALL be documented as unsupported. HTML entities decoded by the parser (e.g., `&#123;`) SHALL be documented as becoming live `{{ }}` holes.

#### Scenario: SVG case corruption documented
- **WHEN** a template contains `<svg viewBox="0 0 1 1">`
- **THEN** the attribute SHALL be lowercased (`viewbox`)
- **AND** the documentation SHALL recommend constructing SVG via the element API instead

#### Scenario: Entity-decoded hole documented
- **WHEN** a template contains `&#123;&#123; x &#125;&#125;` with `x` in the context
- **THEN** the decoded `{{ x }}` SHALL be interpolated
- **AND** this SHALL be documented as the reason no literal-`{{` HTML-entity escape exists

## MODIFIED Requirements

(none — the additions document existing intentional behavior without changing it)
