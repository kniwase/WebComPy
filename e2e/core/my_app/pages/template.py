from webcompy.components import ComponentContext, define_component
from webcompy.signal import use_state
from webcompy.template import render_template


@define_component("template-page")
def TemplatePage(context: ComponentContext[None]):
    context.set_title("Template - E2E")

    count = use_state(lambda: 0)

    def increment(_):
        count.value += 1

    return render_template(
        """
        <div data-testid="template-page">
            <h2>Template Engine Tests</h2>
            <div>
                <span data-testid="count">{{ count }}</span>
                <button data-testid="increment-btn" @click="increment">+</button>
            </div>
            <div>
                <span data-testid="static-text">static content</span>
            </div>
            <ul>
                <li data-testid="item-1">Item 1</li>
                <li data-testid="item-2">Item 2</li>
            </ul>
            <input data-testid="disabled-input" disabled />
        </div>
        """,
        locals(),
    )
