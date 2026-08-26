from __future__ import annotations

import json
import platform
from typing import Any

from webcompy.components import ComponentContext, define_component, on_after_rendering
from webcompy.signal import Signal
from webcompy.template import render_template

from ..parity_fixtures import PARITY_TEMPLATES, compute_parity_results


def _serialize_parsed_dom(node: Any) -> str:
    if node.nodeType == 3:
        return f"#text({node.data!r})"
    return f"{node.nodeName.lower()}({''.join(_serialize_parsed_dom(node.childNodes[i]) for i in range(node.childNodes.length))})"


def compute_parsed_dom_results() -> dict[str, str]:
    from webcompy.ports._browser._raw import browser

    results: dict[str, str] = {}
    for name, source in PARITY_TEMPLATES.items():
        container = browser.document.createElement("div")
        container.innerHTML = source
        results[name] = "".join(
            _serialize_parsed_dom(container.childNodes[i]) for i in range(container.childNodes.length)
        )
    return results


@define_component()
def HtmlParserParityPage(context: ComponentContext[None]):
    context.set_title("HTML Parser Parity - E2E")

    result = Signal("")

    @on_after_rendering
    def compute_in_browser() -> None:
        if platform.system() == "Emscripten":
            result.value = json.dumps(
                {"tree": compute_parity_results(), "dom": compute_parsed_dom_results()},
                sort_keys=True,
            )

    return render_template(
        '<div data-testid="parity-page"><pre data-testid="parity-result">{{ result }}</pre></div>',
        locals(),
    )
