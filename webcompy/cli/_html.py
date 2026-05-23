from __future__ import annotations

import html as html_module
import json
from typing import TYPE_CHECKING, TypeAlias, cast

from webcompy.app._config import PluginScript
from webcompy.components._component import Component
from webcompy.di import inject
from webcompy.elements.typealias import ElementChildren
from webcompy.elements.types import Element, RepeatElement
from webcompy.elements.types._base import ElementWithChildren
from webcompy.ports._keys import DOM_PORT_KEY
from webcompy.signal._computed import computed

if TYPE_CHECKING:
    from webcompy.app._render_context import RenderContext

Scripts: TypeAlias = list[tuple[dict[str, str], str | None]]

PYSCRIPT_VERSION = "2026.3.1"
PYSCRIPT_BASE_URL = f"https://pyscript.net/releases/{PYSCRIPT_VERSION}"


class _DummyParent:
    def __init__(self, node) -> None:
        self._node = node

    def _get_node(self):
        return self._node

    def _get_belonging_component(self):
        return ""

    def _get_belonging_components(self):
        return ()

    def _re_index_children(self, recursive):
        pass


class _HtmlElement(Element):
    def __init__(
        self,
        tag_name: str,
        attrs: dict[str, str],
        *children: ElementChildren,
    ) -> None:
        super().__init__(
            tag_name,  # type: ignore
            attrs,  # type: ignore
            {},
            None,
            children,
        )

    def render_html(self):
        port = inject(DOM_PORT_KEY)
        root_node = port.create_element("div")
        root_node.__webcompy_node__ = False
        root_node.__webcompy_prerendered_node__ = True
        self._parent = cast("ElementWithChildren", _DummyParent(root_node))
        self._node_idx = 0
        self._clear_node_cache()
        self._render()
        root_child = root_node.childNodes[0] if root_node.childNodes.length > 0 else None
        if root_child is None:
            return ""
        return port.render_html(root_child)

    def _get_belonging_component(self):
        return ""

    def _get_belonging_components(self) -> tuple[Component, ...]:
        return tuple([])


class _Loadscreen(_HtmlElement):
    def __init__(self) -> None:
        super().__init__(
            "div",
            {"id": "webcompy-loading"},
            _HtmlElement(
                "style",
                {},
                " ".join(
                    f"{selector}{{"
                    + "".join(
                        name
                        + (
                            "{{{}}}".format("".join(f"{n}:{v};" for n, v in value.items()))
                            if isinstance(value, dict)
                            else f":{value};"
                        )
                        for name, value in props.items()
                    )
                    + "}"
                    for selector, props in self._style.items()
                ),
            ),
            _HtmlElement(
                "div",
                {"class": "wc-loader"},
            ),
        )

    @property
    def _style(self):
        return {
            "#webcompy-loading": {
                "position": "fixed",
                "inset": "0",
                "display": "flex",
                "align-items": "center",
                "justify-content": "center",
                "background": "rgba(0, 0, 0, 0.5)",
                "z-index": "9999",
            },
            ".wc-loader": {
                "border": "12px solid lightgray",
                "border-radius": "50%",
                "border-top": "12px solid skyblue",
                "width": "100px",
                "height": "100px",
                "animation": "spin 1s linear infinite",
            },
            "@keyframes spin": {
                "0%": {
                    "transform": "rotate(0deg)",
                },
                "100%": {
                    "transform": "rotate(360deg)",
                },
            },
        }


def _load_scripts(scripts: Scripts):
    return [
        _HtmlElement(
            "script",
            attrs,
            script,
        )
        for attrs, script in scripts
    ]


def _render_plugin_script(ps: PluginScript) -> _HtmlElement:
    if ps.condition is None:
        return _HtmlElement("script", ps.attrs, ps.script)
    target = "document.head" if ps.in_head else "document.body"
    if "src" in ps.attrs:
        js_parts: list[str] = [
            "(function(){",
            f"  if ({ps.condition}) {{",
            "    var __wc_s = document.createElement('script');",
        ]
        for key, value in ps.attrs.items():
            escaped = json.dumps(value)
            js_parts.append(f"    __wc_s.setAttribute({json.dumps(key)}, {escaped});")
        if ps.script:
            js_parts.append(f"    __wc_s.onload = function() {{ {ps.script} }};")
        js_parts.append(f"    {target}.appendChild(__wc_s);")
        js_parts.extend(["  }", "})();"])
        return _HtmlElement("script", {}, "\n".join(js_parts))
    if not ps.script:
        return _HtmlElement("script", {})
    js_parts = [
        "(function(){",
        f"  if ({ps.condition}) {{",
        f"    {ps.script}",
        "  }",
        "})();",
    ]
    return _HtmlElement("script", {}, "\n".join(js_parts))


def generate_html(
    ctx: RenderContext,
    app_package_name: str,
    dev_mode: bool,
    prerender: bool,
    app_version: str,
    wheel_filename: str,
    pyodide_package_names: list[str] | None = None,
    wasm_local_urls: dict[str, str] | None = None,
    lockfile_url: str | None = None,
    runtime_serving: str = "cdn",
    extra_wheel_filenames: list[str] | None = None,
):
    app = ctx._app
    base_url = ctx.config.base_url
    selector_id = ctx.config.selector.lstrip("#")
    app_root = (
        ctx._root
        if prerender
        else _HtmlElement(
            "div",
            {"id": selector_id, "hidden": ""},
        )
    )
    scripts_head: Scripts = []
    scripts_body: Scripts = []

    core_js_url = (
        f"{base_url}_webcompy-assets/core.js" if runtime_serving == "local" else f"{PYSCRIPT_BASE_URL}/core.js"
    )
    core_css_url = (
        f"{base_url}_webcompy-assets/core.css" if runtime_serving == "local" else f"{PYSCRIPT_BASE_URL}/core.css"
    )

    scripts_head.append(
        (
            {
                "type": "module",
                "src": core_js_url,
            },
            None,
        )
    )

    app_wheel_url = f"{base_url}_webcompy-app-package/{wheel_filename}"
    py_packages = [app_wheel_url]
    if extra_wheel_filenames:
        for name in extra_wheel_filenames:
            py_packages.insert(0, f"{base_url}_webcompy-app-package/{name}")
    for name in pyodide_package_names or []:
        if wasm_local_urls and name in wasm_local_urls:
            py_packages.append(wasm_local_urls[name])
        else:
            py_packages.append(name)
    py_config_dict: dict = {"packages": py_packages, "experimental_create_proxy": "auto"}
    if runtime_serving == "local":
        py_config_dict["interpreter"] = f"{base_url}_webcompy-assets/pyodide/pyodide.mjs"
        py_config_dict["lockFileURL"] = f"{base_url}_webcompy-assets/pyodide/pyodide-lock.json"
    elif lockfile_url is not None:
        py_config_dict["lockFileURL"] = lockfile_url
    py_config = html_module.escape(
        json.dumps(py_config_dict),
        quote=True,
    )
    py_script_lines: list[str] = []
    if ctx.config.profile:
        py_script_lines.append("import time")
        py_script_lines.append("_pyscript_ready = time.perf_counter()")
    py_script_lines.append(f"from {app_package_name}.app import app")
    if ctx.config.profile:
        py_script_lines.append('app._profile_data["pyscript_ready"] = _pyscript_ready')
    py_script_lines.append("app.run()")
    py_script = "\n".join(py_script_lines)
    app_loader_html = f'<script type="py" config="{py_config}">\n{py_script}\n</script>'

    scripts_head.extend(ctx.head["script"])
    scripts_body.extend(ctx.scripts)
    plugin_head_scripts: list[_HtmlElement] = []
    plugin_body_scripts: list[_HtmlElement] = []
    for ps in ctx.config.scripts:
        (plugin_head_scripts if ps.in_head else plugin_body_scripts).append(_render_plugin_script(ps))
    for ps in app._plugin_manager.scripts:
        (plugin_head_scripts if ps.in_head else plugin_body_scripts).append(_render_plugin_script(ps))
    if dev_mode:
        scripts_body.append(
            (
                {"type": "text/javascript"},
                " ".join(
                    (
                        f"var stream = new EventSource('{ctx.config.base_url}_webcompy_reload');",
                        "stream.addEventListener('error', (e) => window.location.reload());",
                    )
                ),
            )
        )

    return "<!doctype html>" + _HtmlElement(
        "html",
        ctx._root.html_attrs,
        _HtmlElement(
            "head",
            {},
            _HtmlElement("title", {}, ctx.head["title"]),
            RepeatElement(
                sequence=computed(lambda: list(ctx.head["meta"].value.values())),
                template=lambda attrs: _HtmlElement("meta", attrs),
            ),
            _HtmlElement("base", {"href": ctx.config.base_url}),
            _HtmlElement(
                "link",
                {"rel": "stylesheet", "href": core_css_url},
            ),
            _HtmlElement(
                "style",
                {"id": "webcompy-scoped-styles"},
                " ".join(
                    (
                        "*[hidden]{display: none;}",
                        ctx.style,
                    )
                ),
            ),
            *[_HtmlElement("link", attrs) for attrs in ctx.head.get("link", [])],
            *_load_scripts(scripts_head),
            *plugin_head_scripts,
        ),
        _HtmlElement(
            "body",
            {},
            _Loadscreen(),
            app_root,
            *_load_scripts(scripts_body),
            *plugin_body_scripts,
        ),
    ).render_html().replace("</body>", f"{app_loader_html}</body>")
