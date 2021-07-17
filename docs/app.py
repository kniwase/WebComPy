from typing import Optional
from webcompy import (
    init_webcompy,
    Reactive,
    WebcompyComponentBase,
    define_component,
    prop,
    ImportCss,
    Style
)


@define_component(
    template="""
<p>
    Count: {{count.value}} times
</p>
<p>
    <button @click="count_up" class="btn btn-secondary btn-sm">
        COUNT UP
    </button>
</p>
""")
class SimpleCounter(WebcompyComponentBase):
    def __init__(self) -> None:
        self.count = Reactive(0)

    def count_up(self):
        self.count.value += 1


@define_component(
    template="""
<h6>
    Counter
</h6>
<p>
    {{count.value}} times
</p>
""")
class CounterDisplay(WebcompyComponentBase):
    def __init__(self) -> None:
        self.count: Reactive[Optional[int]] = Reactive(None)

    @prop('count')
    def on_count_change(self, count: int):
        self.count.value = count


@define_component(
    template="""
<button @click="count_up" class="btn btn-secondary btn-sm">
    COUNT UP
</button>
<button @click="count_down" class="btn btn-secondary btn-sm">
    COUNT Down
</button>
    """,
    styles=[
        Style('h6', {'color': '#364e96'})
    ])
class CounterButton(WebcompyComponentBase):
    def __init__(self) -> None:
        self.count = Reactive(0)

    def count_up(self):
        self.count.value += 1
        self.emit('change', self.count.value)

    def count_down(self):
        self.count.value -= 1
        self.emit('change', self.count.value)


@define_component(
    template="""
<counter-display :count="count.value" />
<counter-button @change="on_change" />
""")
class RichCounter(WebcompyComponentBase):
    def __init__(self) -> None:
        self.count = Reactive(0)

    def on_change(self, count: int):
        self.count.value = count


@define_component(
    template="""
<nav class="navbar navbar-expand-lg navbar-light bg-light">
    <div class="container-fluid">
        <span class="navbar-brand">
            WebcomPy
        </span>
        <button
            class="navbar-toggler"
            type="button"
            data-bs-toggle="collapse"
            data-bs-target="#navbarSupportedContent"
            aria-controls="navbarSupportedContent"
            aria-expanded="false"
            aria-label="Toggle navigation"
        >
            <span class="navbar-toggler-icon"></span>
        </button>
        <div
            class="collapse navbar-collapse"
            id="navbarSupportedContent"
        >
            <ul class="navbar-nav me-auto mb-2 mb-lg-0">
                <li class="nav-item">
                    <a class="nav-link active" href="#/demo-1">
                        DEMO 1
                    </a>
                </li>
                <li class="nav-item">
                    <a class="nav-link active" href="#/demo-2">
                        DEMO 2
                    </a>
                </li>
            </ul>
        </div>
    </div>
</nav>
<router-view />
""")
class WebcompyApp(WebcompyComponentBase):
    pass


init_webcompy(
    components=[
        WebcompyApp,
        CounterDisplay,
        CounterButton,
    ],
    routes=[
        {'path': '/demo-1', 'component': SimpleCounter},
        {'path': '/demo-2', 'component': RichCounter},
    ],
    global_styles=[
        ImportCss(
            'https://cdn.jsdelivr.net/npm/bootstrap@5.0.0-beta1/dist/css/bootstrap.min.css'),
    ]
)
