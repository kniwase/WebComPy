from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.signal import computed
from webcompy.ui._composables import use_theme
from webcompy.ui.theme import Theme


@define_component
def ThemeToggle(_: ComponentContext[None]):
    signal, controller = use_theme()

    label = computed(
        lambda: {
            Theme.LIGHT: "Switch to dark theme",
            Theme.DARK: "Switch to system theme",
            Theme.SYSTEM: "Switch to light theme",
        }[signal.value]
    )

    icon = computed(
        lambda: {
            Theme.LIGHT: "☀",
            Theme.DARK: "🌙",
            Theme.SYSTEM: "🖥",
        }[signal.value]
    )

    return html.BUTTON(
        {
            "type": "button",
            "class": "theme-toggle",
            "aria-label": label,
            "role": "switch",
            "aria-checked": computed(lambda: "true" if signal.value is Theme.DARK else "false"),
            "title": label,
            "@click": lambda _ev: controller.cycle(),
        },
        icon,
    )


ThemeToggle.scoped_style = {
    ".theme-toggle": {
        "display": "inline-flex",
        "align-items": "center",
        "justify-content": "center",
        "width": "2.25rem",
        "height": "2.25rem",
        "padding": "0",
        "font-size": "1.1rem",
        "line-height": "1",
        "background-color": "transparent",
        "color": "var(--color-fg)",
        "border": "1px solid var(--color-border)",
        "border-radius": "var(--radius-sm)",
        "cursor": "pointer",
        "transition": "background-color 0.15s ease, color 0.15s ease",
    },
    ".theme-toggle:hover": {
        "background-color": "var(--color-bg-elevated)",
    },
    ".theme-toggle:focus-visible": {
        "outline": "2px solid var(--color-accent)",
        "outline-offset": "2px",
    },
}
