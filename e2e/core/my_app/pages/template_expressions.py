from __future__ import annotations

from typing import Any

from webcompy.components import ComponentContext, define_component
from webcompy.signal import use_reactive_list, use_state
from webcompy.template import render_template


@define_component()
def TemplateExpressionsPage(context: ComponentContext[None]):
    context.set_title("Template Expressions - E2E")

    count = use_state(lambda: 5)
    name = use_state(lambda: "alice")
    items = use_reactive_list(lambda: [1, 2, 3, 4])

    def increment(_: Any) -> None:
        count.value += 1

    def remove_first(_: Any) -> None:
        if len(items) > 0:
            items.pop(0)

    return render_template(
        """
        <div data-testid="template-expressions-page">
            <h2>Template Expressions Tests</h2>

            <div>
                <span data-testid="arith">{{ count + 1 }}</span>
                <span data-testid="filtered">{{ name | upper }}</span>
                <span data-testid="sub">{{ items[-1] }}</span>
                <span data-testid="reactive-if">
                    {% if count > 5 %}>5{% else %}<=5{% endif %}
                </span>
                <span data-testid="raw-output">{% raw %}{{ literal }}{% endraw %}</span>
                <span data-testid="comment-output">Hello{# world #}!</span>
            </div>

            <div>
                <button data-testid="increment-btn" @click="increment">+</button>
                <button data-testid="remove-first-btn" @click="remove_first">Remove first</button>
            </div>

            <div data-testid="for-section">
                <ul data-testid="for-list">{% for item in items[:3] %}<li data-testid="for-li">{{ item }}</li>{% endfor %}</ul>
            </div>
        </div>
        """,
        {
            "count": count,
            "name": name,
            "items": items,
            "increment": increment,
            "remove_first": remove_first,
        },
    )
