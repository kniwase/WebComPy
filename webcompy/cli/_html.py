from __future__ import annotations
from typing import Optional
from typing_extensions import TypeAlias
from webcompy.elements.types import Element, RepeatElement
from webcompy.elements.typealias import ElementChildren
from webcompy.components._component import Component
from webcompy.reactive._computed import computed
from webcompy.app._app import WebComPyApp
from webcompy.cli._config import WebComPyConfig
from webcompy.utils import strip_multiline_text
from webcompy._version import __version__ as webcompy_version


Scripts: TypeAlias = list[tuple[dict[str, str], Optional[str]]]


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
                            "{{{}}}".format(
                                "".join(f"{n}:{v};" for n, v in value.items())
                            )
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
    app_loader: list[_HtmlElement] = []
    scripts_head: Scripts = []
    scripts_body: Scripts = []

    scripts_head.append(
        (
            {
                "type": "text/javascript",
                "defer": "",
                "src": "https://pyscript.net/alpha/pyscript.js",
            },
            None,
        )
    )
    app_loader.append(
        _HtmlElement(
            "py-script",
            {},
            "\n"
            + strip_multiline_text(
                """
                import micropip, pyodide, js
                from traceback import TracebackException
                async def bootstarp():
                    try:
                        await micropip.install([{dependencies}])
                        from {app_package_name}.bootstrap import app
                        app.__component__.render()
                    except Exception as err:
                        js.console.error("".join(TracebackException.from_exception(err).format()))
                try:
                    pyodide.webloop.WebLoop().run_until_complete(bootstarp())
                except Exception as err:
                    js.console.error("".join(TracebackException.from_exception(err).format()))
                """.format(
                    app_package_name=config.app_package,
                    dependencies=",".join(
                        '"' + p + '"'
                        for p in (
                            *{*config.dependencies, "typing_extensions"},
                            f"{config.base}_webcompy-app-package/webcompy-{webcompy_version}-py3-none-any.whl",
                            f"{config.base}_webcompy-app-package/app-{app_version}-py3-none-any.whl",
                        )
                    ),
                )
            ),
        )
    )

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

    return (
        "<!doctype html>"
        + _HtmlElement(
            "html",
            {},
            _HtmlElement(
                "head",
                {},
                _HtmlElement("title", {}, app.__component__.head["title"]),
                RepeatElement(
                    sequence=computed(
                        lambda: list(app.__component__.head["meta"].value.values())
                    ),
                    template=lambda attrs: _HtmlElement("meta", attrs),
                ),
                _HtmlElement("base", {"href": config.base}),
                _HtmlElement(
                    "style",
                    {},
                    " ".join(
                        (
                            "*[hidden]{display: none;}",
                            "py-script, py-config, py-loader {display: none;}",
                            app.__component__.style,
                        )
                    ),
                ),
                *[
                    _HtmlElement("link", attrs)
                    for attrs in app.__component__.head.get("link", [])
                ],
                *_load_scripts(scripts_head),
            ),
            _HtmlElement(
                "body",
                {},
                _Loadscreen(),
                app_root,
                *_load_scripts(scripts_body),
                *app_loader,
            ),
        ).render_html()
    )
