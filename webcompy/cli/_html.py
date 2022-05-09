from webcompy.elements.types import Element
from webcompy.elements.typealias import ElementChildren
from webcompy.app._app import WebComPyApp
from webcompy.utils import strip_multiline_text
from webcompy.cli._config import WebComPyConfig


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

    def _get_belonging_components(self):
        return tuple()


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


def _load_scripts(scripts: list[tuple[dict[str, str], str | None]]):
    return [
        _HtmlElement(
            "script",
            attrs,
            strip_multiline_text(script if script else ""),
        )
        for attrs, script in scripts
    ]


def generate_html(
    config: WebComPyConfig,
    dev_mode: bool,
    app: WebComPyApp,
    prerender: bool,
):
    base = b if (b := config.base) == "/" else f"{b}/"
    scripts: list[tuple[dict[str, str], str | None]] = [
        (
            {
                "type": "text/javascript",
                "src": f"{base}scripts/brython.js",
            },
            None,
        ),
        (
            {
                "type": "text/javascript",
                "src": f"{base}scripts/brython_stdlib.js",
            },
            None,
        ),
        (
            {
                "type": "text/javascript",
                "src": f"{base}scripts/webcompy.brython.js",
            },
            None,
        ),
        (
            {
                "type": "text/javascript",
                "src": f"{base}scripts/{config.app_package}.brython.js",
            },
            None,
        ),
    ]
    scripts.extend(app.__scripts__)
    scripts.append(
        (
            {"type": "text/python"},
            strip_multiline_text(
                """
                from {app_package}.bootstrap import app
                app.__component__.render()
                """.format(
                    app_package=config.app_package
                )
            ).strip(),
        )
    )
    if dev_mode:
        scripts.append(
            (
                {"type": "text/javascript"},
                strip_multiline_text(
                    """
                    var stream= new EventSource('{base}_webcompy_reload');
                    stream.addEventListener('error', (e) => window.location.reload());
                    """.format(
                        base=base
                    )
                ).strip(),
            )
        )
    if title := app.__head__.get("title"):
        title = _HtmlElement("title", {}, title)
    else:
        title = None
    if dev_mode:
        brython_options = "{debug: 1, cache: false, indexedDB: true}"
    else:
        brython_options = "{debug: 0, cache: true, indexedDB: true}"
    if prerender:
        app_root = app.__component__
    else:
        app_root = _HtmlElement("div", {"id": "webcompy-app", "hidden": ""})
    return (
        "<!doctype html>"
        + _HtmlElement(
            "html",
            {},
            _HtmlElement(
                "head",
                {},
                title,
                *[
                    _HtmlElement("meta", attrs)
                    for attrs in app.__head__.get("meta", [])
                ],
                _HtmlElement("base", {"href": base}),
                _HtmlElement("style", {}, "*[hidden] { display: none; }"),
                _HtmlElement("style", {}, *app.__component__.style.split("\n")),
                *[
                    _HtmlElement("link", attrs)
                    for attrs in app.__head__.get("link", [])
                ],
                *_load_scripts(app.__head__.get("script", [])),
            ),
            _HtmlElement(
                "body",
                {"onload": f"brython({brython_options})"},
                _Loadscreen(),
                app_root,
                *_load_scripts(scripts),
            ),
        ).render_html()
    )
