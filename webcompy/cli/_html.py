from __future__ import annotations

import json
from typing import TypeAlias

from webcompy._version import __version__ as webcompy_version
from webcompy.app._app import WebComPyApp
from webcompy.cli._config import WebComPyConfig
from webcompy.components._component import Component
from webcompy.elements.typealias import ElementChildren
from webcompy.elements.types import Element, RepeatElement
from webcompy.reactive._computed import computed
from webcompy.utils import strip_multiline_text

Scripts: TypeAlias = list[tuple[dict[str, str], str | None]]


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
                {"class": "container"},
                _HtmlElement(
                    "div",
                    {"class": "loader"},
                ),
            ),
        )

    @property
    def _style(self):
        return {
            "body": {
                "margin": "0",
                "padding": "0",
                "box-sizing": "border-box",
                "width": "100vw",
                "height": "100vh",
            },
            ".container": {
                "width": "100%",
                "height": "100%",
                "display": "flex",
                "flex-direction": "column",
                "align-items": "center",
                "justify-content": "center",
                "position": "fixed",
            },
            ".loader": {
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
    config: WebComPyConfig,
    dev_mode: bool,
    prerender: bool,
    app_version: str,
    app: WebComPyApp,
):
    app_root = (
        app.__component__
        if prerender
        else _HtmlElement(
            "div",
            {"id": "webcompy-app", "hidden": ""},
        )
    )
    scripts_head: Scripts = []
    scripts_body: Scripts = []

    scripts_head.append(
        (
            {
                "type": "module",
                "src": "https://pyscript.net/releases/2025.11.1/core.js",
            },
            None,
        )
    )

    py_packages = [
        *{*config.dependencies, "typing_extensions"},
        f"{config.base}_webcompy-app-package/webcompy-{webcompy_version}-py3-none-any.whl",
        f"{config.base}_webcompy-app-package/app-{app_version}-py3-none-any.whl",
    ]
    py_config = json.dumps({"packages": py_packages})
    py_script = strip_multiline_text(
        """
        import micropip, js
        from traceback import TracebackException
        try:
            await micropip.install([{dependencies}])
            from {app_package_name}.bootstrap import app
            app.__component__.render()
        except Exception as err:
            js.console.error("".join(TracebackException.from_exception(err).format()))
        """.format(
            app_package_name=config.app_package_path.name,
            dependencies=",".join('"' + p + '"' for p in py_packages),
        )
    )
    app_loader_html = f"<script type=\"py\" config='{py_config}'>\n{py_script}\n</script>"

    scripts_head.extend(app.__component__.head["script"])
    scripts_body.extend(app.__component__.scripts)
    if dev_mode:
        scripts_body.append(
            (
                {"type": "text/javascript"},
                " ".join(
                    (
                        f"var stream = new EventSource('{config.base}_webcompy_reload');",
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
            _HtmlElement("title", {}, app.__component__.head["title"]),
            RepeatElement(
                sequence=computed(lambda: list(app.__component__.head["meta"].value.values())),
                template=lambda attrs: _HtmlElement("meta", attrs),
            ),
            _HtmlElement("base", {"href": config.base}),
            _HtmlElement(
                "link",
                {"rel": "stylesheet", "href": "https://pyscript.net/releases/2025.11.1/core.css"},
            ),
            _HtmlElement(
                "style",
                {},
                " ".join(
                    (
                        "*[hidden]{display: none;}",
                        app.__component__.style,
                    )
                ),
            ),
            *[_HtmlElement("link", attrs) for attrs in app.__component__.head.get("link", [])],
            *_load_scripts(scripts_head),
        ),
        _HtmlElement(
            "body",
            {},
            _Loadscreen(),
            app_root,
            *_load_scripts(scripts_body),
        ),
    ).render_html().replace("</body>", f"{app_loader_html}</body>")
