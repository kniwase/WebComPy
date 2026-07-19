from __future__ import annotations

from typing import Any

from webcompy.components import ComponentContext, define_component
from webcompy.signal import ReactiveList, use_state
from webcompy.template import render_template


@define_component
def TemplateControlFlowPage(context: ComponentContext[None]):
    context.set_title("Template Control Flow - E2E")

    show = use_state(lambda: True)
    count = use_state(lambda: 0)
    items = use_state(
        lambda: ReactiveList(
            [{"name": "alpha", "visible": True}, {"name": "beta", "visible": False}, {"name": "gamma", "visible": True}]
        )
    )

    def toggle_show(_: Any) -> None:
        show.value = not show.value

    def increment(_: Any) -> None:
        count.value += 1

    return render_template(
        """
        <div data-testid="template-control-flow-page">
            <h2>Template Control Flow Tests</h2>

            <div>
                <span data-testid="if-state">{{ show_label }}</span>
                <button data-testid="toggle-btn" @click="toggle">Toggle</button>
            </div>

            <div data-testid="if-section">
                {% if show %}<p data-testid="if-visible">YES</p>{% else %}<p data-testid="if-hidden">NO</p>{% endif %}
            </div>

            <div data-testid="for-section">
                <ul data-testid="for-list">
                    {% for item in items %}
                        {% if item.visible %}<li data-testid="for-li">{{ item.name }}</li>{% endif %}
                    {% endfor %}
                </ul>
            </div>

            <div>
                <span data-testid="count">{{ count }}</span>
                <button data-testid="increment-btn" @click="increment">+</button>
            </div>
        </div>
        """,
        {
            "show": show,
            "show_label": show,
            "toggle": toggle_show,
            "count": count,
            "increment": increment,
            "items": items,
        },
    )
