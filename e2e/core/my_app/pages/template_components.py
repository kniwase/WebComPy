from webcompy.components import ComponentContext, define_component
from webcompy.signal import Signal, use_state
from webcompy.template import render_template


@define_component
def CardCount(context):
    start = context.props.get("start")
    initial_value = start.value if isinstance(start, Signal) else start

    def increment(_):
        if isinstance(start, Signal):
            start.value = start.value + 1

    return render_template(
        """
        <section data-testid="card-count">
            <p data-testid="card-greeting">Hello, Component Tag!</p>
            <span data-testid="card-count-value">{{ count }}</span>
            <button data-testid="card-increment" @click="increment">+</button>
            <span data-testid="card-initial">{initial}</span>
        </section>
        """,
        {"count": start, "increment": increment, "initial": initial_value},
    )


@define_component
def NestedCount(context):
    start = context.props.get("start")
    initial_value = start.value if isinstance(start, Signal) else start

    return render_template(
        """
        <article data-testid="nested-count">
            <span data-testid="nested-count-value">{{ count }}</span>
            <span data-testid="nested-initial">{initial}</span>
        </article>
        """,
        {"count": start, "initial": initial_value},
    )


@define_component
def TemplateComponentsPage(context: ComponentContext[None]):
    context.set_title("Template Components - E2E")

    outer_count = use_state(lambda: 5)

    return render_template(
        """
        <div data-testid="template-components-page">
            <h2>Component Tags</h2>
            <card-count :start="outer_count" />
            <nested-count :start="outer_count" />
        </div>
        """,
        locals(),
    )
