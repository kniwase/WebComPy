from __future__ import annotations

import html as html_module
import json
from typing import TypeAlias

from webcompy.app._app import WebComPyApp
from webcompy.components._component import Component
from webcompy.elements.typealias import ElementChildren
from webcompy.elements.types import Element, RepeatElement
from webcompy.signal._computed import computed

Scripts: TypeAlias = list[tuple[dict[str, str], str | None]]

PYSCRIPT_VERSION = "2026.3.1"
PYSCRIPT_BASE_URL = f"https://pyscript.net/releases/{PYSCRIPT_VERSION}"


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
        return self._render_html(False, 0)

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


def generate_html(
    app: WebComPyApp,
    dev_mode: bool,
    prerender: bool,
    app_version: str,
    wheel_filename: str,
    pyodide_package_names: list[str] | None = None,
    wasm_local_urls: dict[str, str] | None = None,
    lockfile_url: str | None = None,
    runtime_serving: str = "cdn",
):
    base_url = app.config.base_url
    app_root = (
        app._root
        if prerender
        else _HtmlElement(
            "div",
            {"id": "webcompy-app", "hidden": ""},
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
    if app.config.profile:
        py_script_lines.append("import time")
        py_script_lines.append("_pyscript_ready = time.perf_counter()")
    py_script_lines.append(f"from {app.config.app_package_path.name}.bootstrap import app")
    if app.config.profile:
        py_script_lines.append('app._profile_data["pyscript_ready"] = _pyscript_ready')
    py_script_lines.append("app.run()")
    py_script = "\n".join(py_script_lines)
    app_loader_html = f'<script type="py" config="{py_config}">\n{py_script}\n</script>'

    scripts_head.extend(app.head["script"])
    scripts_body.extend(app.scripts)
    if dev_mode:
        scripts_body.append(
            (
                {"type": "text/javascript"},
                " ".join(
                    (
                        f"var stream = new EventSource('{app.config.base_url}_webcompy_reload');",
                        "stream.addEventListener('error', (e) => window.location.reload());",
                    )
                ),
            )
        )

    return "<!doctype html>" + _HtmlElement(
        "html",
        {},
        _HtmlElement(
            "head",
            {},
            _HtmlElement("title", {}, app.head["title"]),
            RepeatElement(
                sequence=computed(lambda: list(app.head["meta"].value.values())),
                template=lambda attrs: _HtmlElement("meta", attrs),
            ),
            _HtmlElement("base", {"href": app.config.base_url}),
            _HtmlElement(
                "link",
                {"rel": "stylesheet", "href": core_css_url},
            ),
            _HtmlElement(
                "style",
                {},
                " ".join(
                    (
                        "*[hidden]{display: none;}",
                        app.style,
                    )
                ),
            ),
            *[_HtmlElement("link", attrs) for attrs in app.head.get("link", [])],
            *_load_scripts(scripts_head),
        ),
        _HtmlElement(
            "body",
            {},
            _Loadscreen(),
            app_root,
            *_load_scripts(scripts_body),
            "<!--webcompy-app-loader-->",
        ),
    ).render_html().replace("<!--webcompy-app-loader-->", app_loader_html)
