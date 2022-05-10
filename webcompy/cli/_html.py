from typing import TypeAlias
from webcompy.elements.types import Element
from webcompy.elements.typealias import ElementChildren
from webcompy.app._app import WebComPyApp
from webcompy.utils import strip_multiline_text
from webcompy.cli._config import WebComPyConfig


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


def _load_scripts(scripts: Scripts):
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
    title = (
        _HtmlElement("title", {}, title)
        if (title := app.__head__.get("title"))
        else None
    )
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

    if config.environment == "pyscript":
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
        app_loader.extend(
            [
                _HtmlElement(
                    "py-env",
                    {"hidden": ""},
                    "\n"
                    + "\n".join(
                        f"- '{p}'" if p.endswith(".whl") else f"- {p}"
                        for p in config.dependencies
                    )
                    + "\n"
                    + strip_multiline_text(
                        f"""
                        - '{config.base}webcompy-app-package/webcompy-0.0.0-py3-none-any.whl'
                        - '{config.base}webcompy-app-package/app-0.0.0-py3-none-any.whl'
                        """
                    ).strip()
                    + "\n",
                ),
                _HtmlElement(
                    "py-script",
                    {"hidden": ""},
                    "\n"
                    + strip_multiline_text(
                        f"""
                        from {config.app_package}.bootstrap import app
                        app.__component__.render()
                        """
                    ).strip()
                    + "\n",
                ),
            ]
        )
    else:
        scripts_body.extend(
            [
                (
                    {
                        "type": "text/javascript",
                        "src": f"{config.base}webcompy-app-package/brython.js",
                    },
                    None,
                ),
                (
                    {
                        "type": "text/javascript",
                        "src": f"{config.base}webcompy-app-package/brython_stdlib.js",
                    },
                    None,
                ),
                (
                    {
                        "type": "text/javascript",
                        "src": f"{config.base}webcompy-app-package/webcompy.brython.js",
                    },
                    None,
                ),
                (
                    {
                        "type": "text/javascript",
                        "src": f"{config.base}webcompy-app-package/{config.app_package}.brython.js",
                    },
                    None,
                ),
            ]
        )
        app_loader.extend(
            _load_scripts(
                [
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
                    ),
                    (
                        {"type": "text/javascript"},
                        "brython("
                        + (
                            "{debug: 1, cache: false, indexedDB: true}"
                            if dev_mode
                            else "{debug: 0, cache: true, indexedDB: true}"
                        )
                        + ");",
                    ),
                ]
            )
        )

    scripts_head.extend(app.__head__.get("script", []))
    scripts_body.extend(app.__scripts__)
    if dev_mode:
        scripts_body.append(
            (
                {"type": "text/javascript"},
                strip_multiline_text(
                    """
                    var stream= new EventSource('{base}_webcompy_reload');
                    stream.addEventListener('error', (e) => window.location.reload());
                    """.format(
                        base=config.base
                    )
                ).strip(),
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
                title,
                *[
                    _HtmlElement("meta", attrs)
                    for attrs in app.__head__.get("meta", [])
                ],
                _HtmlElement("base", {"href": config.base}),
                _HtmlElement(
                    "style",
                    {},
                    " ".join(("*[hidden]{display: none;}", app.__component__.style)),
                ),
                *[
                    _HtmlElement("link", attrs)
                    for attrs in app.__head__.get("link", [])
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
