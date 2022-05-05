from webcompy.elements.types import Element
from webcompy.elements.typealias import ElementChildren
from webcompy.app._app import WebComPyApp
from webcompy.cli._config import WebComPyConfig


_WEBCOMPY_ESSENTIAL_SCRIPTS = (
    (
        {
            "type": "text/javascript",
            "src": "_scripts/brython.js",
        },
        None,
    ),
    (
        {
            "type": "text/javascript",
            "src": "_scripts/brython_stdlib.js",
        },
        None,
    ),
    (
        {
            "type": "text/javascript",
            "src": "_scripts/webcompy.brython.js",
        },
        None,
    ),
)


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
        return self._render_html(0, 0)

    def _get_belonging_component(self):
        return ""

    def _get_belonging_components(self):
        return tuple()


def _load_scripts(scripts: list[tuple[dict[str, str], str | None]]):
    return [
        _HtmlElement(
            "script",
            attrs,
            *(s.split("\n") if (s := script) else []),
        )
        for attrs, script in scripts
    ]


def generate_html(
    config: WebComPyConfig,
    dev_mode: bool,
    app: WebComPyApp,
    prerender: bool,
):
    scripts: list[tuple[dict[str, str], str | None]] = list(_WEBCOMPY_ESSENTIAL_SCRIPTS)
    scripts.append(
        (
            {
                "type": "text/javascript",
                "src": f"_scripts/{config.app_package}.brython.js",
            },
            None,
        ),
    )
    scripts.extend(app.__scripts__)
    scripts.append(
        (
            {"type": "text/python"},
            f"from {config.app_package} import webcompyapp\nwebcompyapp.__component__.render()",
        )
    )
    if dev_mode:
        scripts.append(
            (
                {"type": "text/javascript"},
                "\n".join(
                    (
                        "var stream= new EventSource('{base}_webcompy_reload');".format(
                            base=b if (b := config.base) == "/" else f"{b}/"
                        ),
                        "stream.addEventListener('error', (e) => { window.location.reload(); });"
                    )
                ),
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
                _HtmlElement("base", {"href": config.base}),
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
                app_root,
                _HtmlElement("div", {"id": "webcompy-loading"}, "loading..."),
                *_load_scripts(scripts),
            ),
        ).render_html()
    )
