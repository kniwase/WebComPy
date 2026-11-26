# Spec Delta

## ADDED Requirements

### Requirement: Elements shall destroy only framework-owned signals on teardown and detachment

Virtual DOM elements (`ElementAbstract` and its subclasses) SHALL NOT implicitly claim caller-supplied `SignalBase` inputs via attribute assignment, and element teardown (`_remove_element`) and branch-patch detachment (`_detach_from_node`) SHALL destroy ONLY signals explicitly registered as owned by that element (framework-created derived computeds allocated by templates or `:bind` expansion, internal element computeds, `@computed_property` members, and component transferable signals). Caller-supplied `Signal`, `Computed`, `ReadonlySignal`, `ReactiveList`, and `ReactiveDict` values passed into elements, templates, or component props SHALL retain their dependency edges across element unmount, switch-branch patching, and element refresh. Each framework-created derived computed SHALL be claimed by at most one owning element or component so nested elements cannot prematurely destroy a parent component's prop.

#### Scenario: RepeatElement preserves caller Computed and reactive collections across conditional unmount and remount
- **WHEN** a `RepeatElement` renders a caller-supplied `Computed`, `ReactiveList`, or `ReactiveDict` inside a conditional `{% if %}` block that toggles off (`_remove_element`) and back on
- **THEN** the caller signal SHALL retain its upstream dependency edges while unmounted and SHALL continue recomputing and updating the DOM after remounting

#### Scenario: TextElement and RawHTMLElement preserve caller Computed across unmount and Switch branch patching
- **WHEN** a `TextElement` or `RawHTMLElement` bound to a caller `Computed` or `ReadonlySignal` is detached during `SwitchElement` patching (`_detach_from_node`) or unmounted (`_remove_element`)
- **THEN** the caller signal SHALL retain its producer edges and SHALL continue delivering updated values when its source signals change

#### Scenario: SwitchElement preserves caller reactive conditions and case list on unmount
- **WHEN** a `SwitchElement` backed by a caller-supplied reactive condition or case-list signal is unmounted
- **THEN** the caller condition or case-list signal SHALL remain intact with all upstream producer edges preserved

#### Scenario: RouterLink preserves caller reactive inputs across refresh and unmount while cleaning internal computeds
- **WHEN** a `RouterLink` receives caller reactive signals for `to`, `text`, `query`, `params`, `path_params`, or `active_class`
- **AND** the `to` signal updates (triggering `_refresh`) or the `RouterLink` unmounts
- **THEN** all caller-supplied signals SHALL remain active and intact
- **AND** internal `RouterLink` computeds (`_href`, `_class_attr`, `_aria_current_attr`) SHALL be destroyed on unmount

#### Scenario: RouterView cleans internal match computed on unmount
- **WHEN** a `RouterView` unmounts via `_remove_element()`
- **THEN** its internal `_level_match` computed SHALL detach from `router.current_match`

#### Scenario: MarkdownForElement preserves caller iterable signal and avoids duplicate allocation on reparenting
- **WHEN** a `MarkdownForElement` renders a caller-supplied reactive iterable and later unmounts, OR when a `MarkdownForElement` over an expression computed is reparented via `_on_set_parent`
- **THEN** the caller iterable SHALL retain its producer edges on unmount
- **AND** reparenting SHALL NOT allocate a second framework-created derived computed
- **AND** any expression-derived framework computed SHALL detach its upstream edges once when the `MarkdownForElement` unmounts

#### Scenario: Component-tag interpolated props survive inner conditional unmounts and clean up on component unmount
- **WHEN** a parent template passes a framework-synthesized derived prop (such as `"Hi {{ name }}"` or `:items="box.items"`) to a child `Component`
- **AND** an element inside the child component conditionally unmounts while the child component remains mounted
- **THEN** the prop computed SHALL NOT be destroyed until the child `Component` itself unmounts or detaches
- **AND** when the child `Component` unmounts or detaches, the prop computed SHALL be destroyed

#### Scenario: Framework-owned element and binding computeds detach from upstream producers on unmount
- **WHEN** an element containing framework-owned derived computeds or internal computeds (template text/attribute/for expressions, radio `:bind` `checked`, `MultiLineTextElement`, dictionary-row representation token, or `AppDocumentRoot` template root attributes) unmounts
- **THEN** all such framework-owned computeds SHALL call `consumer_destroy()` and leave zero lingering consumer edges on upstream user signals

#### Scenario: Observed props ReactiveDict is excluded from component signal transfer members
- **WHEN** a custom-element `Component` with `observed_attributes` initializes its internal `_observed_props` `ReactiveDict`
- **THEN** `"_observed_props"` SHALL NOT appear in `__signal_members__` or `collect_transfer_data()` output
