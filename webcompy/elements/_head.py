from __future__ import annotations

from typing import TYPE_CHECKING

from webcompy.elements._dom_objs import DOMNode
from webcompy.elements.types._base import ElementWithChildren
from webcompy.signal._computed import Computed

if TYPE_CHECKING:
    from webcompy.components._component import HeadPropsStore


class HeadElement(ElementWithChildren):
    __parent: ElementWithChildren

    def __init__(self, head_props: HeadPropsStore) -> None:
        super().__init__()
        self._head_props = head_props
        self._links: list[dict[str, str]] = []
        self._scripts_head: list[tuple[dict[str, str], str | None]] = []
        self._html_attrs: dict[str, str | Computed[str]] = {}

    @property
    def _node_count(self) -> int:
        return 0

    def _get_node(self) -> DOMNode:
        return self._parent._get_node()

    @property
    def _parent(self) -> ElementWithChildren:
        return self.__parent

    @_parent.setter
    def _parent(self, parent: ElementWithChildren):
        self.__parent = parent

    def _render(self):
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

    def get_link_elements_html(self) -> list[str]:
        from webcompy.di import inject
        from webcompy.ports._keys import DOM_PORT_KEY

        port = inject(DOM_PORT_KEY)
        result: list[str] = []
        for attrs in sorted(self._links, key=lambda a: a.get("href", "")):
            el = port.create_element("link")
            for key, value in attrs.items():
                el.setAttribute(key, value)
            result.append(port.render_html(el))
        return result

    def get_script_elements_html(self) -> list[str]:
        from webcompy.di import inject
        from webcompy.ports._keys import DOM_PORT_KEY

        port = inject(DOM_PORT_KEY)
        result: list[str] = []
        for attrs, script in self._scripts_head:
            el = port.create_element("script")
            for key, value in attrs.items():
                el.setAttribute(key, value)
            if script:
                el.textContent = script
            result.append(port.render_html(el))
        return result

    def set_html_attr(self, key: str, value: str | Computed[str]):
        self._html_attrs[key] = value

    def remove_html_attr(self, key: str):
        self._html_attrs.pop(key, None)

    def get_html_attrs(self) -> dict[str, str]:
        return {k: (v.value if isinstance(v, Computed) else v) for k, v in self._html_attrs.items()}
