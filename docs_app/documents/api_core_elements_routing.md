---
title: Elements, Routing & DI API
description: API reference for webcompy.elements, webcompy.router, and webcompy.di.
---

# Elements, Routing & DI API

<!-- author:start:intro -->
API reference for `webcompy.elements` (DOM element constructors, control-flow primitives, boundaries, head props, and HTML tag factories), `webcompy.router`, and `webcompy.di`.
<!-- author:end:intro -->

<!-- generated:start -->

## Elements, Control Flow & Head

### AttrValue

```python
AttrValue: TypeAlias = SignalBase[Any] | str | int | bool
```

Key: `webcompy.elements.typealias._element_property:AttrValue` · Exports: `from webcompy.elements.typealias import AttrValue`

An attribute value: a plain value or a reactive signal providing one.

### break_line

```python
def break_line()
```

Key: `webcompy.elements.generators:break_line` · Exports: `from webcompy.elements import break_line`

Create a line break element.

**Returns:** A `NewLine` element rendering as a `<br>` node.

### client_only

```python
def client_only(
    children: Callable[[], ElementChildren],
    fallback: Callable[[], ElementChildren] | None = None,
) -> ClientOnlyElement
```

Key: `webcompy.elements.generators:client_only` · Exports: `from webcompy.elements import client_only`

Create an element rendered only in the browser.

On server rendering and static generation the `fallback` (or nothing) is emitted instead, keeping browser-only content out of the prerender.

**Args:**

- `children`: Generator producing the browser-only content.
- `fallback`: Generator producing server-side placeholder content.

**Returns:** A `ClientOnlyElement` switching content by environment.

### ClientOnlyElement

```python
class ClientOnlyElement(DynamicElement):
    def __init__(
        self,
        children: Callable[[], ElementChildren],
        fallback: Callable[[], ElementChildren] | None = None,
    ) -> None
```

Key: `webcompy.elements.types._client_only:ClientOnlyElement` · Exports: `from webcompy.elements import ClientOnlyElement`, `from webcompy.elements.types import ClientOnlyElement`

Element whose children render only in the browser environment.

During server rendering and static generation the fallback generator (or an empty text node) is rendered instead; the children generator is evaluated only when client-side rendering and hydration run.

**Args:**

- `children`: Zero-argument callable producing the browser-only children.
- `fallback`: Zero-argument callable producing server-side placeholder children.

### create_element

```python
def create_element(
    tag_name: HtmlTags,
    /,
    attributes: dict[str | EventKey | DomNodeRefKey, AttrValue | EventHandler | DomNodeRef],
    *children: ElementChildren,
) -> Element
```

Key: `webcompy.elements.generators:create_element` · Exports: `from webcompy.elements import create_element`

Create a reactive element of the given tag.

Attribute values accept reactive signals that keep the DOM attribute in sync, event keys from `event()` attach handlers, and `noderef` captures the node in a `DomNodeRef`.

**Args:**

- `tag_name`: HTML tag name.
- `attributes`: Mapping of attribute names (plus `event()`/`noderef` keys) to static or reactive values.
- `*children`: Child elements, strings, or reactive values.

**Returns:** The configured `Element` node.

### DomNodeRef

```python
class DomNodeRef:
    def __init__(self) -> None
```

Key: `webcompy.elements.types._refference:DomNodeRef` · Exports: `from webcompy.elements import DomNodeRef`

Handle to the DOM node mounted for an element created with `noderef`.

Attribute access and assignment transparently proxy to the underlying DOM node, so most DOM APIs can be used on the handle directly.

**Attributes:**

- `element`: The captured DOM node; raises `WebComPyException` when the referenced element is not mounted yet.

#### Members

**`element`** (property)

```python
@property
def element(self) -> DOMNode
```

Return the captured DOM node.

**Raises:**

- `WebComPyException`: When the referenced element is not mounted.

**Returns:** The captured DOM node.

### Element

```python
class Element(ElementBase):
    def __init__(
        self,
        tag_name: HtmlTags,
        attrs: dict[str, AttrValue] | None = None,
        events: dict[str, EventHandler] | None = None,
        ref: DomNodeRef | None = None,
        children: Iterable[ElementChildren] | None = None,
        *,
        preserve_children: bool = False,
    ) -> None
```

Key: `webcompy.elements.types._element:Element` · Exports: `from webcompy.elements.types import Element`, `from webcompy.template import Element`

A DOM element node with attributes, events, children, and a `:bind` option.

Attribute values may be reactive signals, events bind via `event()` keys, `:ref` captures the node in a `DomNodeRef`, and `:bind` sets up two-way form control binding.

**Args:**

- `tag_name`: HTML tag name rendered by this element.
- `attrs`: Attribute name-to-value mapping; values may be reactive.
- `events`: Event name-to-handler mapping.
- `ref`: Reference receiving the created DOM node.
- `children`: Child elements, strings, or reactive values.
- `preserve_children`: When `True` the element's DOM children are managed externally and never reconciled by the framework.

### ElementAbstract

```python
class ElementAbstract(SignalReceivable):
    def __init__(self) -> None
```

Key: `webcompy.elements.types._abstract:ElementAbstract` · Exports: `from webcompy.elements.types import ElementAbstract`, `from webcompy.template import ElementAbstract`

Base class of all virtual DOM nodes.

Manages the lifecycle shared by every element node: DOM node creation, mounting into the parent, hydration adoption of server-rendered nodes, callback cleanup, and explicit framework-owned signal disposal on removal without implicitly claiming borrowed attributes.

### ElementBase

```python
class ElementBase(ElementWithChildren)
```

Key: `webcompy.elements.types._element:ElementBase` · Internal allowlist entry

Base of concrete DOM element nodes.

Handles DOM node creation and hydration adoption, applying the processed attributes, reactive attribute updates, event listeners, and two-way bind property callbacks to the underlying node.

### ElementChildren

```python
ElementChildren: TypeAlias = ElementAbstract | SignalBase[Any] | str | None
```

Key: `webcompy.elements.typealias._element_property:ElementChildren` · Exports: `from webcompy.elements.typealias import ElementChildren`, `from webcompy.template import ElementChildren`

A child node: an element, a reactive value rendering as text, a plain string, or `None`.

### ErrorBoundaryElement

```python
class ErrorBoundaryElement(DynamicElement):
    def __init__(
        self,
        children: Callable[[], ElementChildren],
        fallback: Callable[[Exception, Callable[[], None]], ElementChildren],
        on_error: Callable[[Exception], Any] | None = None,
        catch_events: bool = False,
    ) -> None
```

Key: `webcompy.elements.types._error_boundary:ErrorBoundaryElement` · Exports: `from webcompy.elements import ErrorBoundaryElement`, `from webcompy.elements.types import ErrorBoundaryElement`

Element catching render errors from its children and rendering a fallback.

When child generation or rendering raises, the fallback generator runs with the caught exception and a reset callable, and the fallback children replace the failing tree. `reset()` retries the original children.

**Args:**

- `children`: Zero-argument callable producing the guarded children.
- `fallback`: Callable receiving the caught exception and the `reset` callable, producing replacement children.
- `on_error`: Optional callback invoked with each caught exception.
- `catch_events`: When `True` errors raised by event handlers of descendant elements are also captured by this boundary.

#### Members

**`reset`** (method)

```python
def reset(self) -> None
```

Retry rendering the original children after a fallback was shown.

### event

```python
def event(event_name: str)
```

Key: `webcompy.elements.generators:event` · Exports: `from webcompy.elements import event`

Return an attribute key binding an event handler for `event_name`.

Use the returned key in an `create_element` attribute mapping with a callable value to attach a listener for the named DOM event.

**Args:**

- `event_name`: DOM event name such as `click` or `input`.

**Returns:** Attribute key that routes the corresponding value as an event handler.

### EventHandler

```python
EventHandler: TypeAlias = Callable[[DOMEvent], Any] | Callable[[DOMEvent], Coroutine[Any, Any, Any]]
```

Key: `webcompy.elements.typealias._element_property:EventHandler` · Exports: `from webcompy.elements.typealias import EventHandler`

An event listener callback: a synchronous function or a coroutine receiving a `DOMEvent`.

### FragmentElement

```python
class FragmentElement(DynamicElement):
    def __init__(self, children: list[ElementAbstract] | None = None) -> None
```

Key: `webcompy.elements.types._fragment:FragmentElement` · Exports: `from webcompy.elements.types import FragmentElement`, `from webcompy.template import FragmentElement`

Container rendering its children inline without a DOM wrapper.

**Args:**

- `children`: Child elements placed directly into the parent's DOM node.

### HeadElement

```python
class HeadElement(ElementWithChildren):
    def __init__(self, head_props: HeadPropsStore) -> None
```

Key: `webcompy.elements._head:HeadElement` · Exports: `from webcompy.elements import HeadElement`

Virtual element collecting document head content for an app.

Aggregates the title, meta tags, links, scripts, and styles declared by the application and components, then renders them into the document `<head>` on the browser or as HTML strings during server rendering. Supported for direct configuration or via `app.head(...)`.

**Args:**

- `head_props`: Store shared by the owning app holding the current title and meta state.

**Attributes:**

- `head_data`: Collected head configuration: reactive `title` and `meta` entries plus accumulated `link` and `script` lists.
- `html_attrs`: Attribute name-to-value mapping currently set on the `<html>` element, with reactive values resolved.

#### Members

**`append_link`** (method)

```python
def append_link(self, attributes: dict[str, str])
```

Append a `<link>` element with the given attributes.

**Args:**

- `attributes`: Attribute name-to-value mapping for the link tag.

**`append_script`** (method)

```python
def append_script(self, attributes: dict[str, str], script: str | None = None)
```

Append a `<script>` element.

**Args:**

- `attributes`: Attribute name-to-value mapping for the script tag.
- `script`: Inline script source, or `None` for an external script.

**`append_style`** (method)

```python
def append_style(self, content: str | Computed[str]) -> None
```

Append a `<style>` element to the head.

**Args:**

- `content`: Style sheet content, either static or reactive.

**`get_head_content_html`** (method)

```python
def get_head_content_html(self) -> str
```

Render the collected head content as HTML.

**Returns:** Multi-line HTML string with the title, meta tags, default styles, dynamic styles, and link elements.

**`get_scoped_styles_html`** (method)

```python
def get_scoped_styles_html(self) -> str
```

Render the scoped component style sheets as HTML.

**Returns:** Multi-line HTML string with the component default style plus one `<style>` element per registered component style.

**`head_data`** (property)

```python
@property
def head_data(self) -> dict
```

Return the collected head configuration.

**Returns:** Mapping holding the reactive `title` and `meta` entries plus the accumulated `link` and `script` lists.

**`html_attrs`** (property)

```python
@property
def html_attrs(self) -> dict[str, str]
```

Return resolved attributes currently set on the `<html>` element.

**Returns:** Attribute name-to-value mapping with reactive values resolved.

**`remove_html_attr`** (method)

```python
def remove_html_attr(self, key: str)
```

Remove a previously set attribute from the `<html>` element.

**Args:**

- `key`: Attribute name.

**`set_head`** (method)

```python
def set_head(self, head: Head) -> None
```

Set title, links, scripts, and replace-or-add meta entries.

**Args:**

- `head`: Mapping with optional `title` (str), `meta` (name-to-content mapping), `link` (attribute mappings), and `script` ( `(attributes, source)` pairs ) entries.

**`set_html_attr`** (method)

```python
def set_html_attr(self, key: str, value: str | Computed[str])
```

Set an attribute on the document `<html>` element.

**Args:**

- `key`: Attribute name.
- `value`: Attribute value, either static or reactive.

**`set_meta`** (method)

```python
def set_meta(self, key: str, attributes: dict[str, str])
```

Set the attributes of a meta element registered under `key`.

**Args:**

- `key`: Registry key identifying the meta element.
- `attributes`: Attribute name-to-value mapping for the meta tag.

**`set_title`** (method)

```python
def set_title(self, title: str)
```

Set the document title.

**Args:**

- `title`: New title text.

**`update_head`** (method)

```python
def update_head(self, head: Head) -> None
```

Merge the given head configuration into the current one.

**Args:**

- `head`: Mapping with optional `title` (str), `meta` (name-to-content mapping), `link` (attribute mappings), and `script` ( `(attributes, source)` pairs ) entries; absent keys leave the current configuration untouched.

### HtmlTags

```python
HtmlTags: TypeAlias = ...
```

Key: `webcompy.elements.typealias._html_tag_names:HtmlTags` · Exports: `from webcompy.elements.typealias import HtmlTags`

All HTML tag names accepted by `create_element`, grouped by content category.

### MultiLineTextElement

```python
class MultiLineTextElement(RepeatElement):
    def __init__(self, text: str | SignalBase[Any]) -> None
```

Key: `webcompy.elements.types._repeat:MultiLineTextElement` · Exports: `from webcompy.elements.types import MultiLineTextElement`

Text element rendering each line of a multi-line value as a separate node.

The string (or reactive value) is split on `\n` and each line becomes a text node followed by a `NewLine` element, so the line breaks react to value changes through the underline repeat machinery.

**Args:**

- `text`: Static string or reactive value whose multi-line text is rendered.

### NewLine

```python
class NewLine(ElementAbstract):
    def __init__(self) -> None
```

Key: `webcompy.elements.types._text:NewLine` · Exports: `from webcompy.elements.types import NewLine`

Element rendering as a `<br>` DOM node.

### noderef

```python
noderef = DomNodeRefKey(':ref')
```

Key: `webcompy.elements.generators:noderef` · Exports: `from webcompy.elements import noderef`

Attribute key marking a `DomNodeRef` value that captures the element's DOM node.

### raw_html

```python
def raw_html(html: str | SignalBase[Any], *, wrapper: str = 'span') -> RawHTMLElement
```

Key: `webcompy.elements.generators:raw_html` · Exports: `from webcompy.elements import raw_html`

Create an element injecting raw HTML into a wrapper element.

**Args:**

- `html`: HTML string or reactive value set as `innerHTML`.
- `wrapper`: Tag name of the element the HTML is injected into.

**Returns:** A `RawHTMLElement` rendering the raw HTML.

### repeat

```python
def repeat(
    sequence: SignalBase[dict[K, V]] | SignalBase[list[V]],
    template: Callable[[V], ElementChildren] | Callable[[V, K], ElementChildren],
    key: Callable[[V], K] | None = None,
) -> RepeatElement
```

Key: `webcompy.elements.generators:repeat` · Exports: `from webcompy.elements import repeat`

Create an element repeating `template` for each item of a reactive sequence.

The sequence may be a `ReactiveList` or `ReactiveDict` signal. For keyed updates, the template receives the key as its second argument and `key` derives keys for list items; keyed reconciliation reuses DOM nodes across updates instead of rebuilding them.

**Args:**

- `sequence`: Reactive list or dict signal providing the items.
- `template`: Callable building children for one item, optionally receiving the key as a second argument.
- `key`: Callable deriving a stable key from a list item; disallowed for dict sequences, which are keyed by definition.

**Returns:** A `RepeatElement` that re-renders as the sequence changes.

### RepeatElement

```python
class RepeatElement(DynamicElement):
    def __init__(
        self,
        sequence: SignalBase[dict[K, V]] | SignalBase[list[V]],
        template: Callable[[V], ElementChildren] | Callable[[V, K], ElementChildren],
        key: Callable[[V], K] | None = None,
    ) -> None
```

Key: `webcompy.elements.types._repeat:RepeatElement` · Exports: `from webcompy.elements.types import RepeatElement`

Element rendering one child per item of a reactive sequence.

A `ReactiveList` or `ReactiveDict` signal drives the children. When keys are available (dict items, or list items through `key`), updates reconcile by key and reuse DOM nodes instead of rebuilding them.

**Args:**

- `sequence`: Reactive list or dict signal providing the items.
- `template`: Callable building children for one item, optionally receiving the key as a second argument.
- `key`: Callable deriving a stable key from a list item; disallowed for dict sequences.

**Raises:**

- `ValueError`: When `sequence` is not a signal, or `key` is given for a dict sequence.

### suspense

```python
def suspense(
    *,
    fallback: NodeGenerator,
    children: NodeGenerator,
    error_fallback: NodeGenerator | None = None,
    timeout: float = 10.0,
) -> SuspenseElement
```

Key: `webcompy.elements.generators:suspense` · Exports: `from webcompy.elements import suspense`

Create an element awaiting async child setup before showing children.

The fallback renders while children's async setup resolves; on server environments resolution block rendering up to `timeout` seconds.

**Args:**

- `fallback`: Generator rendered while the children are pending.
- `children`: Generator producing the content shown once resolved.
- `error_fallback`: Generator rendered when child async setup raises.
- `timeout`: Seconds to wait for async resolution before falling back.

**Returns:** A `SuspenseElement` managing the pending/resolved states.

### SuspenseElement

```python
class SuspenseElement(DynamicElement):
    def __init__(
        self,
        fallback: Callable[[], ElementChildren],
        children: Callable[[], ElementChildren],
        error_fallback: Callable[[], ElementChildren] | None = None,
        timeout: float = 10.0,
    ) -> None
```

Key: `webcompy.elements.types._suspense:SuspenseElement` · Exports: `from webcompy.elements import SuspenseElement`, `from webcompy.elements.types import SuspenseElement`

Element awaiting async child setup, showing fallback content meanwhile.

The fallback renders while the children generator and any pending async component setup inside it resolve; once resolved (or timed out or failed with an error fallback) the appropriate content replaces the fallback, patching the DOM to reuse untouched nodes.

**Args:**

- `fallback`: Zero-argument callable producing the pending placeholder.
- `children`: Zero-argument callable producing the content shown once all async setup resolves.
- `error_fallback`: Zero-argument callable producing content shown when child async setup raises.
- `timeout`: Seconds to await async resolution before using the fallback (or error fallback) instead.

### switch

```python
def switch(*cases: SwitchCase, default: NodeGenerator | None = None)
```

Key: `webcompy.elements.generators:switch` · Exports: `from webcompy.elements import switch`

Create an element rendering the first case whose condition is truthy.

**Args:**

- `*cases`: `SwitchCase` pairs of a reactive condition and a child generator.
- `default`: Generator rendered when no case condition is truthy.

**Returns:** A `SwitchElement` swapping its children as conditions change.

### SwitchCases

```python
SwitchCases: TypeAlias = SwitchCasesSignal | SwitchCasesSignalList
```

Key: `webcompy.elements.types._switch:SwitchCases` · Exports: `from webcompy.elements.types import SwitchCases`

Case list: a static `(condition, generator)` list or a reactive signal of it.

### SwitchElement

```python
class SwitchElement(DynamicElement):
    def __init__(self, cases: SwitchCases, default: NodeGenerator | None) -> None
```

Key: `webcompy.elements.types._switch:SwitchElement` · Exports: `from webcompy.elements.types import SwitchElement`

Element rendering the first case whose condition is truthy.

Conditions may be reactive values or plain values; when any signals change, the first matching branch re-renders, patching reused DOM nodes and swapping the rest.

**Args:**

- `cases`: Static list of `(condition, generator)` pairs, or a reactive signal providing it.
- `default`: Generator rendered when no case condition is truthy.

### TeleportElement

```python
class TeleportElement(DynamicElement):
    def __init__(self, props: TeleportProps, *children: ElementChildren) -> None
```

Key: `webcompy.elements.types._teleport:TeleportElement` · Exports: `from webcompy.elements import TeleportElement`, `from webcompy.elements.types import TeleportElement`

Element rendering its children inside a remote DOM target.

The children are mounted into the first element matching the `to` CSS selector, while an anchor comment node marks the position in the source tree (or the children render inline when no target matches). Targets shared by multiple teleports interleave their children by registration.

**Args:**

- `props`: Mapping holding the `to` CSS selector and the optional `ssr` flag (default `True`) controlling server-side emission of the children into the resolved target.
- `*children`: Child elements, strings, or reactive values moved to the target container.

**Raises:**

- `ValueError`: When the `to` selector is not a non-empty static string.

### text

```python
def text(text: str | SignalBase[Any], enable_multiline: bool = True)
```

Key: `webcompy.elements.generators:text` · Exports: `from webcompy.elements import text`, `from webcompy.elements.html import TEXT`

Create a text node element, replacing line breaks with newline elements.

**Args:**

- `text`: Static string or reactive value rendered as text.
- `enable_multiline`: When `True` render each line as a text node followed by a `NewLine`; otherwise render the plain string.

**Returns:** A `TextElement` or `MultiLineTextElement`.

### TextElement

```python
class TextElement(ElementAbstract):
    def __init__(self, text: str | SignalBase[Any]) -> None
```

Key: `webcompy.elements.types._text:TextElement` · Exports: `from webcompy.elements.types import TextElement`

Text node element whose content may track a reactive value.

**Args:**

- `text`: Static string rendered as a single text node, or a reactive value whose changes update the node's text content.

### TransitionElement

```python
class TransitionElement(DynamicElement):
    def __init__(
        self,
        props: dict[str, Any],
        child_generator: Callable[[], ElementChildren],
    ) -> None
```

Key: `webcompy.elements.types._transition:TransitionElement` · Exports: `from webcompy.elements import TransitionElement`, `from webcompy.elements.types import TransitionElement`

Element animating enter/leave transitions for a single conditional child.

The child generator must yield at most one element with a single DOM node. When it changes, CSS classes named after the `name` prop drive the enter/leave phases (`{name}-enter-from` etc.), and the leaving node is removed only after its transition or animation finishes.

**Args:**

- `props`: Mapping with the `name` (class prefix) and optional `duration` (milliseconds) props.
- `child_generator`: Zero-argument callable producing the single child element, or `None` to remove it.

**Raises:**

- `WebComPyException`: When the `name` prop is missing or the `duration` prop is not a non-negative finite number.

## Router & Navigation

### create_typed_route

```python
def create_typed_route(
    *,
    params_type: type[ParamsType] = dict[str, Any],
    query_type: type[QueryParamsType] = dict[str, str],
    path_params_type: type[PathParamsType] = dict[str, str],
) -> TypedRoute[ParamsType, QueryParamsType, PathParamsType]
```

Key: `webcompy.router._component:create_typed_route` · Exports: `from webcompy.router import create_typed_route`

Build a typed `(context, link)` pair for route declarations.

The returned tuple parameterizes `TypedRouterContext` and `TypedRouterLink` with the given param types.

**Args:**

- `params_type`: Type of the navigation state param dict.
- `query_type`: Type of the query param dict.
- `path_params_type`: Type of the path param dict.

**Returns:** A tuple of the matching `TypedRouterContext` and `TypedRouterLink` parameterizations.

### lazy

```python
def lazy(import_path: str, caller_file: str) -> ComponentGenerator
```

Key: `webcompy.router._lazy:lazy` · Exports: `from webcompy.router import lazy`

Create a lazily-resolved component generator for a route.

**Args:**

- `import_path`: `"module:Attribute"` path of the generator to resolve on demand.
- `caller_file`: Path of the file declaring the lazy route.

**Returns:** A `LazyComponentGenerator` resolving `import_path` on first use.

**Raises:**

- `WebComPyRouterException`: If `import_path` is not in the `"module:Attribute"` form, uses a relative module path, or `caller_file` is empty.

### LazyComponentGenerator

```python
class LazyComponentGenerator(ComponentGenerator):
    def __init__(self, import_path: str, caller_file: str) -> None
```

Key: `webcompy.router._lazy:LazyComponentGenerator` · Exports: `from webcompy.router import LazyComponentGenerator`

A `ComponentGenerator` that resolves its real generator on demand.

The underlying generator is imported lazily at `"module:Attribute"` on first use, keeping the route module out of the initial bundle. Attribute lookups and style handling delegate to the resolved generator.

**Args:**

- `import_path`: `"module:Attribute"` path of the generator.
- `caller_file`: Path of the file that declared the lazy route.

**Attributes:**

- `scoped_style`: Compiled scoped style declarations, resolved from the underlying generator.

#### Members

**`scoped_style`** (property)

```python
@property
def scoped_style(self)
```

Scoped component style of the resolved generator.

**Returns:** The scoped style mapping of the underlying generator.

### RoutedComponent

```python
RoutedComponent = ComponentContext[RouterContext]
```

Key: `webcompy.router._component:RoutedComponent` · Exports: `from webcompy.router import RoutedComponent`

Component context of a component rendered by the router with a `RouterContext`.

### Router

```python
class Router:
    def __init__(
        self,
        *pages: RouterPage,
        default: ComponentGenerator[TypedRouterContext[Any, Any, Any]] | None = None,
        history: HistoryPort | None = None,
        mode: Literal['hash', 'history'] = 'hash',
        base_url: str = '',
        preload: bool = True,
    ) -> None
```

Key: `webcompy.router._router:Router` · Exports: `from webcompy.router import Router`

Route table with nested page chains and navigation hooks.

Builds flat route matchers from nested `RouterPage` declarations, resolves the current match reactively, and runs an async-capable guard pipeline before committing navigations through the history port.

**Args:**

- `*pages`: Route page declarations.
- `default`: Component rendered when no route matches, or `None` for a "Not Found" fallback.
- `history`: History port driving the current path. When `None`, the port is resolved from the DI scope on first use.
- `mode`: Routing mode (`"hash"` or `"history"`). Ignored when `history` is provided.
- `base_url`: Leading path segment stripped from paths in `"history"` mode.
- `preload`: Whether lazy routes are preloaded when the router starts.

**Attributes:**

- `before_route_change`: Hooks run before a route change commits.
- `after_route_change`: Hooks run after a route change committed.
- `on_route_error`: Handlers invoked when route resolution or guard execution fails.
- `current_match`: `Computed[RouteMatch | None]` for the active path; `None` when no route matches.

#### Members

**`current_match`** (method)

```python
def current_match(self)
```

Current match for the active path.

**Returns:** A `Computed[RouteMatch | None]` whose `.value` is the matching `RouteMatch`, or `None` when no route matches the current path.

**Raises:**

- `Exception`: If route matching raises and no `on_route_error` handler suppresses the error.

**`preload_lazy_routes`** (method)

```python
def preload_lazy_routes(self, *, force: bool = False) -> None
```

Resolve lazy route components ahead of navigation.

**Args:**

- `force`: Resolve even when `preload` was disabled at construction.

### RouterContext

```python
RouterContext: TypeAlias = TypedRouterContext[dict[str, Any], dict[str, str], dict[str, str]]
```

Key: `webcompy.router._context:RouterContext` · Exports: `from webcompy.router import RouterContext`

Type alias of `TypedRouterContext` with untyped parameter dicts.

### RouterKey

```python
RouterKey = InjectKey[Router]('webcompy-router')
```

Key: `webcompy.router._keys:RouterKey` · Exports: `from webcompy.router import RouterKey`

DI key under which the application `Router` is provided.

### RouterLink

```python
RouterLink: TypeAlias = TypedRouterLink[dict[str, Any], dict[str, str], dict[str, str]]
```

Key: `webcompy.router._link:RouterLink` · Exports: `from webcompy.router import RouterLink`

Type alias of `TypedRouterLink` with untyped parameter dicts.

### RouterView

```python
class RouterView(DynamicElement):
    def __init__(self) -> None
```

Key: `webcompy.router._view:RouterView` · Exports: `from webcompy.router import RouterView`

Dynamic element rendering the component for the currently matched route level.

Each `RouterView` renders one level of the matched route chain and reuses the mounted component while that level's identity is unchanged across navigations.

### use_router

```python
def use_router() -> Router
```

Key: `webcompy.router._composables:use_router` · Exports: `from webcompy.router import use_router`

Resolve the application `Router` from the active DI scope.

**Returns:** The `Router` provided in the current DI scope.

## Dependency Injection

### DIScope

```python
class DIScope:
    def __init__(
        self,
        providers: dict[object, Any] | None = None,
        parent: DIScope | None = None,
    ) -> None
```

Key: `webcompy.di._scope:DIScope` · Exports: `from webcompy import DIScope`, `from webcompy.di import DIScope`

Provider map with parent delegation, child scopes, and disposal.

`inject` resolves keys from the local provider map, then from the parent scope. Callable providers (that are not classes) are invoked lazily on first injection and cached. `dispose` marks the scope and all descendants as disposed; injection on a disposed scope falls through to the parent or `default`.

**Args:**

- `providers`: Initial key-to-value mappings for the scope.
- `parent`: Parent scope consulted when a key is not local.

#### Members

**`create_child`** (method)

```python
def create_child(self) -> DIScope
```

Create a child scope with this scope as parent.

**Returns:** The new child `DIScope` instance.

**Raises:**

- `RuntimeError`: If the scope has been disposed.

**`dispose`** (method)

```python
def dispose(self) -> None
```

Dispose this scope, all child scopes, and its providers.

**`inject`** (method)

```python
def inject(self, key: object, default: Any = _MISSING) -> Any
```

Resolve a key from this scope, delegating to the parent.

**Args:**

- `key`: Dependency key to resolve.
- `default`: Value to return when the key is not provided. When omitted, resolution failure raises `InjectionError`.

**Returns:** The value provided for `key`.

**Raises:**

- `InjectionError`: If the key is not provided (in this scope, its parent, or any ancestor) and no `default` is given.

**`provide`** (method)

```python
def provide(self, key: object, value: Any) -> None
```

Register a value for a key in this scope.

**Args:**

- `key`: Dependency key to register.
- `value`: Provider value stored for the key.

**Raises:**

- `RuntimeError`: If the scope has been disposed.

### HYDRATION_DATA_KEY

```python
HYDRATION_DATA_KEY = InjectKey[dict[str, Any]]('webcompy-hydration-data')
```

Key: `webcompy.di._keys:HYDRATION_DATA_KEY` · Exports: `from webcompy.di import HYDRATION_DATA_KEY`, `from webcompy.hydration import HYDRATION_DATA_KEY`

Key for the pending async-result payload transferred from SSR to the hydrated client.

### HYDRATION_SIGNAL_DATA_KEY

```python
HYDRATION_SIGNAL_DATA_KEY = InjectKey[dict[str, dict[str, Any]]]('webcompy-hydration-signal-data')
```

Key: `webcompy.di._keys:HYDRATION_SIGNAL_DATA_KEY` · Exports: `from webcompy.di import HYDRATION_SIGNAL_DATA_KEY`

Key for the signal value payload transferred from SSR to the hydrated client.

### inject

```python
def inject(key: object, default: Any = _MISSING) -> Any
```

Key: `webcompy.di:inject` · Exports: `from webcompy import inject`, `from webcompy.di import inject`, `from webcompy.hydration import inject`, `from webcompy.template import inject`

Resolve a dependency from the active DI scope.

Looks up `key` in the currently active `DIScope` (or the app-level scope when no render scope is active), delegating to parent scopes.

**Args:**

- `key`: Dependency key to resolve.
- `default`: Value to return when the key is not provided. When omitted, resolution failure raises `InjectionError`.

**Returns:** The value provided for `key`.

**Raises:**

- `InjectionError`: If the key is not provided and no `default` is given.

### InjectionError

```python
class InjectionError(Exception):
    def __init__(self, key: object) -> None
```

Key: `webcompy.di._exceptions:InjectionError` · Exports: `from webcompy import InjectionError`, `from webcompy.di import InjectionError`

Raised when a dependency key has no provider in any scope.

**Args:**

- `key`: Dependency key that could not be resolved. `InjectKey` instances and types are rendered by name in the message.

### InjectKey

```python
class InjectKey(Generic[T]):
    def __init__(self, name: str) -> None
```

Key: `webcompy.di._key:InjectKey` · Exports: `from webcompy import InjectKey`, `from webcompy.di import InjectKey`

Typed, identity-based key for dependency injection lookups.

Keys compare and hash by identity rather than by name, so two keys created with the same name remain distinct. The type parameter documents the value type provided under the key.

**Args:**

- `name`: Human-readable name used in messages and `repr`.

**Attributes:**

- `name`: Human-readable name of the key, set at construction.

#### Members

**`name`** (property)

```python
@property
def name(self) -> str
```

Human-readable name of the key, set at construction.

### provide

```python
def provide(key: object, value: Any) -> None
```

Key: `webcompy.di:provide` · Exports: `from webcompy import provide`, `from webcompy.di import provide`

Provide a value for a dependency key in the active DI scope.

Registers `key` with `value` in the currently active `DIScope`. When no render scope is active, the app-level DI scope is used.

**Args:**

- `key`: Dependency key to register (an `InjectKey` or a type).
- `value`: Provider value stored for the key.

**Raises:**

- `InjectionError`: If no active scope and no app-level scope exists.

### RESOURCE_DATA_KEY

```python
RESOURCE_DATA_KEY = InjectKey[dict[str, str]]('webcompy-resource-data')
```

Key: `webcompy.di._keys:RESOURCE_DATA_KEY` · Exports: `from webcompy.di import RESOURCE_DATA_KEY`

Key for the cached app-package resource payload transferred from SSR to the hydrated client.

### RPC_MIDDLEWARE_KEY

```python
RPC_MIDDLEWARE_KEY = InjectKey[object]('webcompy-rpc-middleware')
```

Key: `webcompy.di._keys:RPC_MIDDLEWARE_KEY` · Exports: `from webcompy.rpc import RPC_MIDDLEWARE_KEY`

Key for the per-context `RpcMiddlewareRegistry` consulted by HTTP RPC operations.

### SUSPENSE_RESOLVING_KEY

```python
SUSPENSE_RESOLVING_KEY = InjectKey[bool]('webcompy-internal-suspense-resolving')
```

Key: `webcompy.di._keys:SUSPENSE_RESOLVING_KEY` · Exports: `from webcompy.di import SUSPENSE_RESOLVING_KEY`

Key for the flag set while a `Suspense` boundary is resolving its async children.

## HTML Tag Factories

| Symbol | Key | Signature | Summary |
| --- | --- | --- | --- |
| `A` | `webcompy.elements.html.html_tags:A` | `A = partial(create_element, 'a')` | HTML `<a>` element factory. |
| `ABBR` | `webcompy.elements.html.html_tags:ABBR` | `ABBR = partial(create_element, 'abbr')` | HTML `<abbr>` element factory. |
| `ADDRESS` | `webcompy.elements.html.html_tags:ADDRESS` | `ADDRESS = partial(create_element, 'address')` | HTML `<address>` element factory. |
| `AREA` | `webcompy.elements.html.html_tags:AREA` | `AREA = partial(create_element, 'area')` | HTML `<area>` element factory. |
| `ARTICLE` | `webcompy.elements.html.html_tags:ARTICLE` | `ARTICLE = partial(create_element, 'article')` | HTML `<article>` element factory. |
| `ASIDE` | `webcompy.elements.html.html_tags:ASIDE` | `ASIDE = partial(create_element, 'aside')` | HTML `<aside>` element factory. |
| `AUDIO` | `webcompy.elements.html.html_tags:AUDIO` | `AUDIO = partial(create_element, 'audio')` | HTML `<audio>` element factory. |
| `B` | `webcompy.elements.html.html_tags:B` | `B = partial(create_element, 'b')` | HTML `<b>` element factory. |
| `BDI` | `webcompy.elements.html.html_tags:BDI` | `BDI = partial(create_element, 'bdi')` | HTML `<bdi>` element factory. |
| `BDO` | `webcompy.elements.html.html_tags:BDO` | `BDO = partial(create_element, 'bdo')` | HTML `<bdo>` element factory. |
| `BLOCKQUOTE` | `webcompy.elements.html.html_tags:BLOCKQUOTE` | `BLOCKQUOTE = partial(create_element, 'blockquote')` | HTML `<blockquote>` element factory. |
| `BR` | `webcompy.elements.html.html_tags:BR` | `BR = lambda: break_line()` | HTML `<br>` element factory. |
| `BUTTON` | `webcompy.elements.html.html_tags:BUTTON` | `BUTTON = partial(create_element, 'button')` | HTML `<button>` element factory. |
| `CANVAS` | `webcompy.elements.html.html_tags:CANVAS` | `CANVAS = partial(create_element, 'canvas')` | HTML `<canvas>` element factory. |
| `CAPTION` | `webcompy.elements.html.html_tags:CAPTION` | `CAPTION = partial(create_element, 'caption')` | HTML `<caption>` element factory. |
| `CITE` | `webcompy.elements.html.html_tags:CITE` | `CITE = partial(create_element, 'cite')` | HTML `<cite>` element factory. |
| `CODE` | `webcompy.elements.html.html_tags:CODE` | `CODE = partial(create_element, 'code')` | HTML `<code>` element factory. |
| `COL` | `webcompy.elements.html.html_tags:COL` | `COL = partial(create_element, 'col')` | HTML `<col>` element factory. |
| `COLGROUP` | `webcompy.elements.html.html_tags:COLGROUP` | `COLGROUP = partial(create_element, 'colgroup')` | HTML `<colgroup>` element factory. |
| `DATA` | `webcompy.elements.html.html_tags:DATA` | `DATA = partial(create_element, 'data')` | HTML `<data>` element factory. |
| `DATALIST` | `webcompy.elements.html.html_tags:DATALIST` | `DATALIST = partial(create_element, 'datalist')` | HTML `<datalist>` element factory. |
| `DD` | `webcompy.elements.html.html_tags:DD` | `DD = partial(create_element, 'dd')` | HTML `<dd>` element factory. |
| `DEL` | `webcompy.elements.html.html_tags:DEL` | `DEL = partial(create_element, 'del')` | HTML `<del>` element factory. |
| `DETAILS` | `webcompy.elements.html.html_tags:DETAILS` | `DETAILS = partial(create_element, 'details')` | HTML `<details>` element factory. |
| `DFN` | `webcompy.elements.html.html_tags:DFN` | `DFN = partial(create_element, 'dfn')` | HTML `<dfn>` element factory. |
| `DIALOG` | `webcompy.elements.html.html_tags:DIALOG` | `DIALOG = partial(create_element, 'dialog')` | HTML `<dialog>` element factory. |
| `DIV` | `webcompy.elements.html.html_tags:DIV` | `DIV = partial(create_element, 'div')` | HTML `<div>` element factory. |
| `DL` | `webcompy.elements.html.html_tags:DL` | `DL = partial(create_element, 'dl')` | HTML `<dl>` element factory. |
| `DT` | `webcompy.elements.html.html_tags:DT` | `DT = partial(create_element, 'dt')` | HTML `<dt>` element factory. |
| `EM` | `webcompy.elements.html.html_tags:EM` | `EM = partial(create_element, 'em')` | HTML `<em>` element factory. |
| `EMBED` | `webcompy.elements.html.html_tags:EMBED` | `EMBED = partial(create_element, 'embed')` | HTML `<embed>` element factory. |
| `FIELDSET` | `webcompy.elements.html.html_tags:FIELDSET` | `FIELDSET = partial(create_element, 'fieldset')` | HTML `<fieldset>` element factory. |
| `FIGCAPTION` | `webcompy.elements.html.html_tags:FIGCAPTION` | `FIGCAPTION = partial(create_element, 'figcaption')` | HTML `<figcaption>` element factory. |
| `FIGURE` | `webcompy.elements.html.html_tags:FIGURE` | `FIGURE = partial(create_element, 'figure')` | HTML `<figure>` element factory. |
| `FOOTER` | `webcompy.elements.html.html_tags:FOOTER` | `FOOTER = partial(create_element, 'footer')` | HTML `<footer>` element factory. |
| `FORM` | `webcompy.elements.html.html_tags:FORM` | `FORM = partial(create_element, 'form')` | HTML `<form>` element factory. |
| `H1` | `webcompy.elements.html.html_tags:H1` | `H1 = partial(create_element, 'h1')` | HTML `<h1>` element factory. |
| `H2` | `webcompy.elements.html.html_tags:H2` | `H2 = partial(create_element, 'h2')` | HTML `<h2>` element factory. |
| `H3` | `webcompy.elements.html.html_tags:H3` | `H3 = partial(create_element, 'h3')` | HTML `<h3>` element factory. |
| `H4` | `webcompy.elements.html.html_tags:H4` | `H4 = partial(create_element, 'h4')` | HTML `<h4>` element factory. |
| `H5` | `webcompy.elements.html.html_tags:H5` | `H5 = partial(create_element, 'h5')` | HTML `<h5>` element factory. |
| `H6` | `webcompy.elements.html.html_tags:H6` | `H6 = partial(create_element, 'h6')` | HTML `<h6>` element factory. |
| `HEADER` | `webcompy.elements.html.html_tags:HEADER` | `HEADER = partial(create_element, 'header')` | HTML `<header>` element factory. |
| `HR` | `webcompy.elements.html.html_tags:HR` | `HR = partial(create_element, 'hr')` | HTML `<hr>` element factory. |
| `I` | `webcompy.elements.html.html_tags:I` | `I = partial(create_element, 'i')` | HTML `<i>` element factory. |
| `IFRAME` | `webcompy.elements.html.html_tags:IFRAME` | `IFRAME = partial(create_element, 'iframe')` | HTML `<iframe>` element factory. |
| `IMG` | `webcompy.elements.html.html_tags:IMG` | `IMG = partial(create_element, 'img')` | HTML `<img>` element factory. |
| `INPUT` | `webcompy.elements.html.html_tags:INPUT` | `INPUT = partial(create_element, 'input')` | HTML `<input>` element factory. |
| `INS` | `webcompy.elements.html.html_tags:INS` | `INS = partial(create_element, 'ins')` | HTML `<ins>` element factory. |
| `KBD` | `webcompy.elements.html.html_tags:KBD` | `KBD = partial(create_element, 'kbd')` | HTML `<kbd>` element factory. |
| `LABEL` | `webcompy.elements.html.html_tags:LABEL` | `LABEL = partial(create_element, 'label')` | HTML `<label>` element factory. |
| `LEGEND` | `webcompy.elements.html.html_tags:LEGEND` | `LEGEND = partial(create_element, 'legend')` | HTML `<legend>` element factory. |
| `LI` | `webcompy.elements.html.html_tags:LI` | `LI = partial(create_element, 'li')` | HTML `<li>` element factory. |
| `MAIN` | `webcompy.elements.html.html_tags:MAIN` | `MAIN = partial(create_element, 'main')` | HTML `<main>` element factory. |
| `MAP` | `webcompy.elements.html.html_tags:MAP` | `MAP = partial(create_element, 'map')` | HTML `<map>` element factory. |
| `MARK` | `webcompy.elements.html.html_tags:MARK` | `MARK = partial(create_element, 'mark')` | HTML `<mark>` element factory. |
| `MATH` | `webcompy.elements.html.html_tags:MATH` | `MATH = partial(create_element, 'math')` | HTML `<math>` element factory. |
| `MENU` | `webcompy.elements.html.html_tags:MENU` | `MENU = partial(create_element, 'menu')` | HTML `<menu>` element factory. |
| `METER` | `webcompy.elements.html.html_tags:METER` | `METER = partial(create_element, 'meter')` | HTML `<meter>` element factory. |
| `NAV` | `webcompy.elements.html.html_tags:NAV` | `NAV = partial(create_element, 'nav')` | HTML `<nav>` element factory. |
| `OBJECT` | `webcompy.elements.html.html_tags:OBJECT` | `OBJECT = partial(create_element, 'object')` | HTML `<object>` element factory. |
| `OL` | `webcompy.elements.html.html_tags:OL` | `OL = partial(create_element, 'ol')` | HTML `<ol>` element factory. |
| `OPTGROUP` | `webcompy.elements.html.html_tags:OPTGROUP` | `OPTGROUP = partial(create_element, 'optgroup')` | HTML `<optgroup>` element factory. |
| `OPTION` | `webcompy.elements.html.html_tags:OPTION` | `OPTION = partial(create_element, 'option')` | HTML `<option>` element factory. |
| `OUTPUT` | `webcompy.elements.html.html_tags:OUTPUT` | `OUTPUT = partial(create_element, 'output')` | HTML `<output>` element factory. |
| `P` | `webcompy.elements.html.html_tags:P` | `P = partial(create_element, 'p')` | HTML `<p>` element factory. |
| `PARAM` | `webcompy.elements.html.html_tags:PARAM` | `PARAM = partial(create_element, 'param')` | HTML `<param>` element factory. |
| `PICTURE` | `webcompy.elements.html.html_tags:PICTURE` | `PICTURE = partial(create_element, 'picture')` | HTML `<picture>` element factory. |
| `PORTAL` | `webcompy.elements.html.html_tags:PORTAL` | `PORTAL = partial(create_element, 'portal')` | HTML `<portal>` element factory. |
| `PRE` | `webcompy.elements.html.html_tags:PRE` | `PRE = partial(create_element, 'pre')` | HTML `<pre>` element factory. |
| `PROGRESS` | `webcompy.elements.html.html_tags:PROGRESS` | `PROGRESS = partial(create_element, 'progress')` | HTML `<progress>` element factory. |
| `Q` | `webcompy.elements.html.html_tags:Q` | `Q = partial(create_element, 'q')` | HTML `<q>` element factory. |
| `RP` | `webcompy.elements.html.html_tags:RP` | `RP = partial(create_element, 'rp')` | HTML `<rp>` element factory. |
| `RT` | `webcompy.elements.html.html_tags:RT` | `RT = partial(create_element, 'rt')` | HTML `<rt>` element factory. |
| `RUBY` | `webcompy.elements.html.html_tags:RUBY` | `RUBY = partial(create_element, 'ruby')` | HTML `<ruby>` element factory. |
| `S` | `webcompy.elements.html.html_tags:S` | `S = partial(create_element, 's')` | HTML `<s>` element factory. |
| `SAMP` | `webcompy.elements.html.html_tags:SAMP` | `SAMP = partial(create_element, 'samp')` | HTML `<samp>` element factory. |
| `SECTION` | `webcompy.elements.html.html_tags:SECTION` | `SECTION = partial(create_element, 'section')` | HTML `<section>` element factory. |
| `SELECT` | `webcompy.elements.html.html_tags:SELECT` | `SELECT = partial(create_element, 'select')` | HTML `<select>` element factory. |
| `SMALL` | `webcompy.elements.html.html_tags:SMALL` | `SMALL = partial(create_element, 'small')` | HTML `<small>` element factory. |
| `SOURCE` | `webcompy.elements.html.html_tags:SOURCE` | `SOURCE = partial(create_element, 'source')` | HTML `<source>` element factory. |
| `SPAN` | `webcompy.elements.html.html_tags:SPAN` | `SPAN = partial(create_element, 'span')` | HTML `<span>` element factory. |
| `STRONG` | `webcompy.elements.html.html_tags:STRONG` | `STRONG = partial(create_element, 'strong')` | HTML `<strong>` element factory. |
| `SUB` | `webcompy.elements.html.html_tags:SUB` | `SUB = partial(create_element, 'sub')` | HTML `<sub>` element factory. |
| `SUMMARY` | `webcompy.elements.html.html_tags:SUMMARY` | `SUMMARY = partial(create_element, 'summary')` | HTML `<summary>` element factory. |
| `SUP` | `webcompy.elements.html.html_tags:SUP` | `SUP = partial(create_element, 'sup')` | HTML `<sup>` element factory. |
| `SVG` | `webcompy.elements.html.html_tags:SVG` | `SVG = partial(create_element, 'svg')` | HTML `<svg>` element factory. |
| `TABLE` | `webcompy.elements.html.html_tags:TABLE` | `TABLE = partial(create_element, 'table')` | HTML `<table>` element factory. |
| `TBODY` | `webcompy.elements.html.html_tags:TBODY` | `TBODY = partial(create_element, 'tbody')` | HTML `<tbody>` element factory. |
| `TD` | `webcompy.elements.html.html_tags:TD` | `TD = partial(create_element, 'td')` | HTML `<td>` element factory. |
| `TEXTAREA` | `webcompy.elements.html.html_tags:TEXTAREA` | `TEXTAREA = partial(create_element, 'textarea')` | HTML `<textarea>` element factory. |
| `TFOOT` | `webcompy.elements.html.html_tags:TFOOT` | `TFOOT = partial(create_element, 'tfoot')` | HTML `<tfoot>` element factory. |
| `TH` | `webcompy.elements.html.html_tags:TH` | `TH = partial(create_element, 'th')` | HTML `<th>` element factory. |
| `THEAD` | `webcompy.elements.html.html_tags:THEAD` | `THEAD = partial(create_element, 'thead')` | HTML `<thead>` element factory. |
| `TIME` | `webcompy.elements.html.html_tags:TIME` | `TIME = partial(create_element, 'time')` | HTML `<time>` element factory. |
| `TR` | `webcompy.elements.html.html_tags:TR` | `TR = partial(create_element, 'tr')` | HTML `<tr>` element factory. |
| `TRACK` | `webcompy.elements.html.html_tags:TRACK` | `TRACK = partial(create_element, 'track')` | HTML `<track>` element factory. |
| `U` | `webcompy.elements.html.html_tags:U` | `U = partial(create_element, 'u')` | HTML `<u>` element factory. |
| `UL` | `webcompy.elements.html.html_tags:UL` | `UL = partial(create_element, 'ul')` | HTML `<ul>` element factory. |
| `VAR` | `webcompy.elements.html.html_tags:VAR` | `VAR = partial(create_element, 'var')` | HTML `<var>` element factory. |
| `VIDEO` | `webcompy.elements.html.html_tags:VIDEO` | `VIDEO = partial(create_element, 'video')` | HTML `<video>` element factory. |
| `WBR` | `webcompy.elements.html.html_tags:WBR` | `WBR = partial(create_element, 'wbr')` | HTML `<wbr>` element factory. |

<!-- generated:end -->

## Next steps

<!-- author:start:see-also -->
- Core guides: [Elements & Events](/documents/basic/elements-and-events) and [Routing](/documents/basic/routing).
- Advanced guides: [Routing Deep Dive](/documents/advanced/routing-deep-dive), [Dependency Injection Deep Dive](/documents/advanced/dependency-injection-deep-dive), [Transition](/documents/advanced/transition), [Teleport](/documents/advanced/teleport), and [Async Rendering & Boundaries](/documents/advanced/async-rendering-and-boundaries).
<!-- author:end:see-also -->
