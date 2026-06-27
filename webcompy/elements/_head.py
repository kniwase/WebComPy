from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

from webcompy.elements._dom_objs import DOMNode
from webcompy.elements.types._base import ElementWithChildren
from webcompy.signal._computed import Computed

if TYPE_CHECKING:
    from webcompy.components._component import HeadPropsStore
    from webcompy.signal._base import CallbackConsumerNode


def _wrap_in_layer(content: str) -> str:
    return f"@layer webcompy-dynamic {{ {content} }}"


def _resolve_content(content: str | Computed[str]) -> str:
    if isinstance(content, Computed):
        return content.value
    return content


class HeadElement(ElementWithChildren):
    __parent: ElementWithChildren

    def __init__(self, head_props: HeadPropsStore) -> None:
        super().__init__()
        self._head_props = head_props
        self._links: list[dict[str, str]] = []
        self._scripts_head: list[tuple[dict[str, str], str | None]] = []
        self._styles: list[str | Computed[str]] = []
        self._style_callbacks: dict[int, CallbackConsumerNode] = {}
        self._html_attrs: dict[str, str | Computed[str]] = {}
        self._callback_consumers: dict[str, CallbackConsumerNode] = {}
        self._app_meta_id = uuid4()

        from webcompy.utils import ENVIRONMENT

        if ENVIRONMENT == "pyscript":
            from webcompy.di import inject
            from webcompy.ports._keys import DOM_PORT_KEY

            def updte_title(title: str | None):
                if title is not None:
                    inject(DOM_PORT_KEY).set_title(title)

            consumer = head_props.title.on_after_updating(updte_title)
            self._callback_consumers["__title__"] = consumer

    @property
    def _node_count(self) -> int:
        return 0

    def _get_node(self) -> DOMNode:
        return self.__parent._get_node()

    @property
    def _parent(self) -> ElementWithChildren:
        return self.__parent

    @_parent.setter
    def _parent(self, parent: ElementWithChildren):
        self.__parent = parent

    def set_title(self, title: str):
        if self._head_props is not None:
            self._head_props._app_title = title

    def set_meta(self, key: str, attributes: dict[str, str]):
        if self._head_props is not None:
            meta = self._head_props.head_metas.get(self._app_meta_id, {})
            meta[key] = attributes
            self._head_props.head_metas[self._app_meta_id] = meta

    def append_link(self, attributes: dict[str, str]):
        self._links.append(attributes)

    def append_script(
        self,
        attributes: dict[str, str],
        script: str | None = None,
    ):
        self._scripts_head.append((attributes, script))

    def append_style(self, content: str | Computed[str]) -> None:
        idx = len(self._styles)
        self._styles.append(content)
        if isinstance(content, Computed):
            from webcompy.utils import ENVIRONMENT

            if ENVIRONMENT == "pyscript":
                from webcompy.di import inject
                from webcompy.ports._keys import DOM_PORT_KEY

                def _subscribe_callback(v: str, _idx: int = idx) -> None:
                    _dom = inject(DOM_PORT_KEY)
                    head_el = _dom.query_selector("head")
                    if head_el is None:
                        return
                    sel = f'style[data-webcompy-dynamic="{_idx}"]'
                    el = _dom.query_selector(sel)
                    if el is None:
                        el = _dom.create_element("style")
                        el.setAttribute("data-webcompy-dynamic", str(_idx))
                        el.textContent = _wrap_in_layer(v)
                        head_el.appendChild(el)
                    else:
                        el.textContent = _wrap_in_layer(v)

                self._style_callbacks[idx] = content.on_after_updating(_subscribe_callback)

    def set_head(self, head):
        self.set_title(head.get("title", ""))
        for key, value in head.get("meta", {}).items():
            self.set_meta(key, value)
        self._links.clear()
        self._links.extend(head.get("link", []))
        self._scripts_head.clear()
        self._scripts_head.extend(head.get("script", []))

    def update_head(self, head):
        if "title" in head:
            self.set_title(head["title"])
        for key, meta in head.get("meta", {}).items():
            self.set_meta(key, meta)
        for link in head.get("link", []):
            self.append_link(link)
        for attrs, script in head.get("script", []):
            self.append_script(attrs, script)

    @property
    def head_data(self) -> dict:
        assert self._head_props is not None
        return {
            "title": self._head_props.title,
            "meta": self._head_props.head_meta,
            "link": self._links,
            "script": self._scripts_head,
        }

    async def _render(self):
        from webcompy.di import inject
        from webcompy.di._keys import _COMPONENT_STORE_KEY
        from webcompy.ports._keys import DOM_PORT_KEY
        from webcompy.utils import ENVIRONMENT

        if ENVIRONMENT != "pyscript":
            return

        _dom = inject(DOM_PORT_KEY)
        head_el = _dom.query_selector("head")
        if not head_el:
            return

        if not _dom.get_element_by_id("webcompy-scoped-styles"):
            style_el = _dom.create_element("style")
            style_el.setAttribute("id", "webcompy-scoped-styles")
            style_el.textContent = "*[hidden]{display: none;}"
            head_el.appendChild(style_el)

        store = inject(_COMPONENT_STORE_KEY)
        for gen in store.components.values():
            cid = gen._id
            css = gen.scoped_style
            if css and not _dom.query_selector(f'style[data-webcompy-cid="{cid}"]'):
                el = _dom.create_element("style")
                el.setAttribute("data-webcompy-cid", cid)
                el.textContent = css
                head_el.appendChild(el)

            for idx, rx_style in enumerate(getattr(gen, "_reactive_styles", [])):
                attr_value = f"{cid}-{idx}"
                selector_attr = f'style[data-webcompy-cid-rx="{attr_value}"]'
                existing = _dom.query_selector(selector_attr)
                if existing is None:
                    el = _dom.create_element("style")
                    el.setAttribute("data-webcompy-cid-rx", attr_value)
                    el.textContent = rx_style.render_css(cid)
                    head_el.appendChild(el)
                else:
                    existing.textContent = rx_style.render_css(cid)

        for idx, content in enumerate(self._styles):
            selector_attr = f'style[data-webcompy-dynamic="{idx}"]'
            existing = _dom.query_selector(selector_attr)
            wrapped = _wrap_in_layer(_resolve_content(content))
            if existing is None:
                el = _dom.create_element("style")
                el.setAttribute("data-webcompy-dynamic", str(idx))
                el.textContent = wrapped
                head_el.appendChild(el)
            else:
                existing.textContent = wrapped

        self._reconcile_html_attrs(_dom)

    def _reconcile_html_attrs(self, _dom):
        html_el = _dom.query_selector("html")
        for key, value in self._html_attrs.items():
            current = html_el.getAttribute(key) if html_el else None
            expected = value.value if isinstance(value, Computed) else value
            if current != expected and html_el:
                html_el.setAttribute(key, expected)

    def set_html_attr(self, key: str, value: str | Computed[str]):
        from webcompy.signal._graph import consumer_destroy
        from webcompy.utils import ENVIRONMENT

        if key in self._callback_consumers:
            consumer_destroy(self._callback_consumers[key])
            del self._callback_consumers[key]
        self._html_attrs[key] = value
        if isinstance(value, Computed) and ENVIRONMENT == "pyscript":
            from webcompy.di import inject
            from webcompy.ports._keys import DOM_PORT_KEY

            consumer = value.on_after_updating(
                lambda v, k=key: el.setAttribute(k, v) if (el := inject(DOM_PORT_KEY).query_selector("html")) else None
            )
            self._callback_consumers[key] = consumer
        if ENVIRONMENT == "pyscript":
            from webcompy.di import inject
            from webcompy.ports._keys import DOM_PORT_KEY

            _dom = inject(DOM_PORT_KEY)
            html_el = _dom.query_selector("html")
            if html_el:
                html_el.setAttribute(key, value.value if isinstance(value, Computed) else value)

    def remove_html_attr(self, key: str):
        from webcompy.signal._graph import consumer_destroy
        from webcompy.utils import ENVIRONMENT

        if key in self._callback_consumers:
            consumer_destroy(self._callback_consumers[key])
            del self._callback_consumers[key]
        if key in self._html_attrs:
            del self._html_attrs[key]
        if ENVIRONMENT == "pyscript":
            from webcompy.di import inject
            from webcompy.ports._keys import DOM_PORT_KEY

            _dom = inject(DOM_PORT_KEY)
            html_el = _dom.query_selector("html")
            if html_el:
                html_el.removeAttribute(key)

    def _cleanup_consumers(self):
        from webcompy.signal._graph import consumer_destroy

        for consumer in self._callback_consumers.values():
            consumer_destroy(consumer)
        self._callback_consumers.clear()
        for consumer in self._style_callbacks.values():
            consumer_destroy(consumer)
        self._style_callbacks.clear()

    @property
    def html_attrs(self) -> dict[str, str]:
        return {k: (v.value if isinstance(v, Computed) else v) for k, v in self._html_attrs.items()}

    def get_head_content_html(self) -> str:
        from webcompy.di import inject
        from webcompy.di._keys import _COMPONENT_STORE_KEY
        from webcompy.ports._keys import DOM_PORT_KEY

        port = inject(DOM_PORT_KEY)
        parts: list[str] = []

        title = self._head_props.title.value
        if title:
            el = port.create_element("title")
            el.textContent = str(title)
            parts.append(port.render_html(el))

        for _key, attrs in sorted(self._head_props.head_meta.value.items()):
            el = port.create_element("meta")
            for k, v in attrs.items():
                el.setAttribute(k, v)
            parts.append(port.render_html(el))

        el = port.create_element("style")
        el.setAttribute("id", "webcompy-scoped-styles")
        el.textContent = "*[hidden]{display: none;}"
        parts.append(port.render_html(el))

        store = inject(_COMPONENT_STORE_KEY)
        for _name in sorted(store.components.keys()):
            gen = store.components[_name]
            cid = gen._id
            css = gen.scoped_style
            if css:
                el = port.create_element("style")
                el.setAttribute("data-webcompy-cid", cid)
                el.textContent = css
                parts.append(port.render_html(el))

            for idx, rx_style in enumerate(getattr(gen, "_reactive_styles", [])):
                attr_value = f"{cid}-{idx}"
                el = port.create_element("style")
                el.setAttribute("data-webcompy-cid-rx", attr_value)
                el.textContent = rx_style.render_css(cid)
                parts.append(port.render_html(el))

        for idx, content in enumerate(self._styles):
            el = port.create_element("style")
            el.setAttribute("data-webcompy-dynamic", str(idx))
            el.textContent = _wrap_in_layer(_resolve_content(content))
            parts.append(port.render_html(el))

        for attrs in sorted(self._links, key=lambda a: a.get("href", "")):
            el = port.create_element("link")
            for k, v in attrs.items():
                el.setAttribute(k, v)
            parts.append(port.render_html(el))

        return "\n".join(parts)
