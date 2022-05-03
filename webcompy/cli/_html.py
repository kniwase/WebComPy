from webcompy.elements.types import Element
from webcompy.elements.typealias import ElementChildren
from webcompy.components._component import Component


class HtmlElement(Element):
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


def generate_html(
    app_package_name: str,
    component_styles: str,
    base: str,
    dev_mode: bool,
    app: Component | None,
):
    return (
        "<!doctype html>"
        + HtmlElement(
            "html",
            {},
            HtmlElement(
                "head",
                {},
                HtmlElement("base", {"href": base}),
                HtmlElement("meta", {"charset": "utf-8"}),
                HtmlElement("style", {}, "[hidden] { display: none; }"),
                HtmlElement("style", {}, *component_styles.split("\n")),
            ),
            HtmlElement(
                "body",
                {
                    "onload": "brython({debug: 1, cache: false, indexedDB: true})"
                    if dev_mode
                    else "brython({debug: 0, cache: true, indexedDB: true})"
                },
                HtmlElement("div", {"id": "webcompy-loading"}, "loading..."),
                app
                if app
                else HtmlElement("div", {"id": "webcompy-app", "hidden": ""}),
                HtmlElement(
                    "script",
                    {
                        "type": "text/javascript",
                        "src": "_scripts/brython.js",
                    },
                ),
                HtmlElement(
                    "script",
                    {
                        "type": "text/javascript",
                        "src": "_scripts/brython_stdlib.js",
                    },
                ),
                HtmlElement(
                    "script",
                    {
                        "type": "text/javascript",
                        "src": "_scripts/webcompy.brython.js",
                    },
                ),
                HtmlElement(
                    "script",
                    {
                        "type": "text/javascript",
                        "src": f"_scripts/{app_package_name}.brython.js",
                    },
                ),
                HtmlElement(
                    "script",
                    {"type": "text/python"},
                    f"from {app_package_name} import webcompyapp\n",
                    "webcompyapp.__component__.render()",
                ),
            ),
        ).render_html()
    )
