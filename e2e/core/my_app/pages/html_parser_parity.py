from __future__ import annotations

import json
import platform

from webcompy.components import ComponentContext, define_component, on_after_rendering
from webcompy.signal import Signal
from webcompy.template import render_template

from ..parity_fixtures import compute_parity_results


@define_component
def HtmlParserParityPage(context: ComponentContext[None]):
    context.set_title("HTML Parser Parity - E2E")

    result = Signal("")

    @on_after_rendering
    def compute_in_browser() -> None:
        if platform.system() == "Emscripten":
            result.value = json.dumps(compute_parity_results(), sort_keys=True)

    return render_template(
        '<div data-testid="parity-page"><pre data-testid="parity-result">{{ result }}</pre></div>',
        locals(),
    )
