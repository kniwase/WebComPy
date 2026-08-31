# Design: feat-ui-form-controls

## Context

The `forms` capability provides `Field[T]` (`.value: Signal[T]`, `.errors: Computed[list[str]]`, `.valid`/`.invalid`, `.touched`/`.dirty`, `reset()`), `Form` aggregation, and validators. The `:bind` element attribute already accepts a `Field` and wires interaction state automatically: value sync, `dirty` on write-back, `touched` on blur (elements `_bind.py`, forms spec requirement "`:bind` shall wire Field interaction state"). What does not exist is the rendered, accessible control layer — applications currently hand-build inputs and the ARIA/error wiring.

Grounded facts (verified in codebase):

- `:bind` supports `input[type=text|email|password|search|tel|url|number|checkbox|radio]` and `textarea`, chains with user event handlers, and sets Field interaction state — headless controls reuse this mechanism internally rather than reimplementing write-back. It does **not** yet support `select`; this change extends it (D7).
- `:bind` expansion runs inside `HTMLElementElement.__init__` (`elements/types/_element.py`), so passing `":bind"` in the attrs dict of `create_element` is sufficient for headless controls to reuse the mechanism.
- All UI components are named Light DOM custom elements: `@define_component(custom_element_name=...)` with `headless-*` for headless and `webcompy-*` for themed (Spinner/Dropdown/Modal established this). The custom-element wrapper adds one DOM level around the native control, but Light DOM keeps native form participation and id-based ARIA references working across the wrapper.
- Generated DOM ids are derived from the component instance's hydration-stable `transfer_id` (sanitized, `#` replaced with `-`) — the `overlay_dom_id` pattern established by the overlay components. uuid-based ids are NOT hydration-stable and are retired for this area.
- Each component creates its DI scope as a child of its parent component's DI scope (`components/_component.py`), and `context.provide()` registers in the component's own scope, so a value provided by FormField is resolvable by controls rendered inside its slots.
- Function-style components with `TypedDict` props are the established authoring pattern; reactive props flow as Signals/Computeds.
- `primitives.css` (foundation change) is the themed-style delivery point, imported by `/_webcompy-ui/index.css`.

## Goals / Non-Goals

**Goals:**

- Headless/themed pairs for Input, Textarea, Select, Checkbox, Switch, Radio/RadioGroup plus the FormField wrapper.
- A binding contract that works with `Field` instances (full validation/interaction state) and with plain value/change props (uncontrolled use).
- Correct accessibility wiring centralized in FormField (label association, `aria-invalid`, `aria-describedby` error linkage, touched-gated error display).
- Hydration-stable association ids so SSR output and the hydrated client tree carry the same ids.

**Non-Goals:**

- Custom listbox/combobox, pickers, upload widgets, layout systems, server-side form actions, new validators (see proposal Non-goals). `:bind` on select covers single selection only.

## Decisions

### D1: Binding contract — Field instance or raw value props

Every control accepts either a `field` prop (a `Field` instance) or `value` + `on_change` props. With `field`, the control binds via the existing `:bind` mechanism (value sync, dirty/touched wiring comes for free). With raw props, the control is a plain controlled element (an internal signal seeded from `value`, write-back chained to `on_change`). A plain (non-`Signal`) `value` is an initial seed only: component setup runs once, so later external changes to a plain value are unobservable and only the control's internal state moves; live programmatic sync requires passing a `Signal`, which the control binds through `:bind` in both directions. Rationale: `field` covers the dominant validated-form case with zero wiring; raw props keep the controls usable outside the forms module (search boxes, filters) without forcing Field adoption. The two modes are mutually exclusive per instance; passing both is an error.

### D2: Native elements as the base

Controls render native `<input>`, `<textarea>`, `<select>`, checkbox/radio inputs. Native elements provide keyboard behavior, mobile semantics, and form participation for free; the framework adds binding and ARIA state on top. The custom listbox Select is explicitly deferred (combobox ARIA is a large surface). Themed styling of native controls uses token-based rules (including focus-visible rings) without resetting essential native behavior.

### D3: FormField centralizes label/error ARIA wiring, ids via DI

`FormField` composes: a `<label>` associated with the control, the control slot, and an error message region. Slot contents are rendered elements, so props cannot be injected into a slotted control; instead FormField provides its generated association ids through a component-scoped DI context (`context.provide` of a `FormFieldContext` carrying `control_id`, `error_id`, and label text). Bound controls `inject` the context (with `default=None`) and, when present, set `id` on their native element to `control_id` and, in the touched-invalid state, `aria-describedby` to the `error_id`. When the bound field is touched and invalid, the control also carries `aria-invalid="true"`; otherwise the association is absent. Error display gating on `touched` follows the forms capability's design (no error flash on page load, since touched/dirty are transient and never SSR-transferred). Ids are derived from FormField's `transfer_id` (sanitized like `overlay_dom_id`), making them unique per instance, stable across re-renders, and identical between SSR output and the hydrated client tree. Controls used outside a FormField remain fully functional without the context.

### D4: Switch is a checkbox with role="switch"

Switch renders a checkbox input with `role="switch"` and `aria-checked` reflecting state; binding follows the checkbox path. Rationale: `role="switch"` is the correct ARIA pattern for on/off toggles and keeps native checkbox keyboard behavior (Space to toggle).

### D5: RadioGroup renders items from an options prop

RadioGroup accepts `options` (value/label pairs) plus a `legend`, renders `fieldset` + `legend` and one native radio per option sharing a generated `name` derived from the instance's `transfer_id`, so native arrow-key navigation within the group works without custom keyboard code. Group value binds to a single `Field` or raw value/change props carrying the selected item's string value. The `options`-prop form (rather than slotted `Radio` children) keeps the shared `name` inside the group where it is generated; the `Radio` control remains exported for custom compositions where the author supplies the name.

### D6: Invalid-state styling hook via data-state

Bound controls expose `data-state="invalid"` when the bound field is invalid and touched (matching display gating), and `data-state="valid"` otherwise, following the headless contract's `data-state` vocabulary requirement and the overlay components' precedent. The vocabulary is documented per component (this spec). Themed and headless users style invalid state off this attribute rather than a one-off `data-invalid` attribute.

### D7: `:bind` extended to `<select>`

`expand_bind_attr` gains a `select` path mirroring text inputs: bound attribute `value`, write-back on `change` (select's native commit event), string-valued Signal requirement (no coercion, option values are strings), `blur` marks the Field touched, and `value` participates in the property-attr sync so Signal→DOM changes update the selection. Explicit `value` on the element combined with `:bind` remains a conflict; `option` stays unsupported; `select[multiple]` combined with `:bind` is rejected (single selection only). This keeps the single binding mechanism (no control-level reimplementation) and matches the delta spec's "bind through the framework's `:bind` mechanism". The elements spec's reject-unsupported-elements requirement drops its now-false "select rejected" scenario, so it is replaced (REMOVED + renamed ADDED per the delta tooling contract).

### D8: FormFieldContext data contract

A frozen dataclass `FormFieldContext` (`control_id: str`, `error_id: str`, `label: str`) is provided under a module-private `InjectKey` in the headless package. The context carries only association ids and the label text; validation state flows from the `Field` that both FormField and the control already hold, so there is no second source of truth for touched/invalid. Slot contents evaluate **eagerly in the enclosing render pass** (component functions run at call time; template slot children are bound lazily when the provider calls `context.slots()`), so the provider must run before slot evaluation: the headless FormField provides its own context (ids from its transfer id) before calling `context.slots`, and the themed wrapper — which produces the slot in its own pass — instead generates the ids from the themed instance's transfer id, provides them, and forwards the same values to the headless wrapper through optional `control_id`/`error_id` props. A sibling FormField must never resolve another sibling's leaked context, so the headless wrapper always provides (never injects) its own context. `provide()` leaves the newly created child scope as the active DI scope, which would leak the context forward to components rendered after the provider in the same parent pass; both wrappers therefore confine the provision to the provider's own render pass with a helper that restores the previously active scope once the pass completes (verified for both the function-call slot form and the template slot form). The framework-level root cause (`provide` not restoring the active scope) is deferred to a separate change.

### D9: FormField label vs group legend

`<label for>` cannot associate with a `fieldset`, so FormField and RadioGroup coordinate by convention: when the slotted control is a RadioGroup, the application omits `label` on FormField and passes `legend` to RadioGroup (the group self-labels); FormField still provides the error region and `aria-describedby` wiring. For labelable controls (Input/Textarea/Select/Checkbox/Switch), FormField's `label` renders `<label for=control_id>`. An empty `label` renders no `<label>` element.

### D10: Custom element naming

Headless controls register as `headless-input`, `headless-textarea`, `headless-select`, `headless-checkbox`, `headless-switch`, `headless-radio`, `headless-radio-group`, `headless-form-field`; themed variants as `webcompy-input`, `webcompy-textarea`, `webcompy-select`, `webcompy-checkbox`, `webcompy-switch`, `webcompy-radio`, `webcompy-radio-group`, `webcompy-form-field`, following the Spinner/overlay naming scheme.

## Risks / Tradeoffs

- **Native Select limitations**: styling native `<select>` is constrained across browsers (option lists render natively). Accepted for v1 correctness; custom widget is the documented upgrade path.
- **`:bind` select extension touches the elements layer**: the requirement is modified (rejection of select removed). The write-back shape is a direct mirror of the text path, so risk is low; E2E for `:bind` (`test_form_fields.py`, `test_two_way_binding.py`) must keep passing.
- **DI context dependency**: FormField wiring relies on child-component DI scopes resolving through the parent component's scope (verified in `components/_component.py`), and on slot contents evaluating eagerly during the provider's render pass (verified during implementation for both the function-call form and the template form: component functions run at call time, and template slot children bind lazily when the provider calls `context.slots`). Because `provide` leaves the created child scope active, an unconfined provision leaks the context forward to controls rendered after the provider as siblings — observed during review to give standalone controls a foreign `control_id` (duplicate DOM ids) and wrong `aria-describedby`. The wrappers confine the provision to their own render pass (D8) and never inject a possibly-sibling context; if resolution failed, wiring would silently degrade to standalone behavior. Dedicated unit tests pin the provide/inject path end to end, including sibling isolation in both slot forms. The framework-level root cause (no restore of the active scope in `provide`) is deferred to a separate change.
- **`aria-describedby` absence**: the control must omit the attribute (not emit an empty value) outside the touched-invalid state; the reactive attribute pipeline's None/absence semantics are verified during implementation.
- **Themed native control quirks**: focus rings and invalid states must remain visible across themes; covered by token-driven rules and E2E visual checks in docs demos.
- **Field required for FormField**: FormField's `field` prop is mandatory (it owns the error region); raw value-mode controls are used standalone, not wrapped in FormField.
