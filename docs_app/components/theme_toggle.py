from webcompy.components import ComponentContext, define_component
from webcompy.elements import html, raw_html
from webcompy.signal import use_computed
from webcompy.ui.theme import Theme, use_theme

_SUN_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" '
    'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
    'stroke-linejoin="round" aria-hidden="true">'
    '<circle cx="12" cy="12" r="4"></circle>'
    '<path d="M12 2v2"></path><path d="M12 20v2"></path>'
    '<path d="m4.93 4.93 1.41 1.41"></path><path d="m17.66 17.66 1.41 1.41"></path>'
    '<path d="M2 12h2"></path><path d="M20 12h2"></path>'
    '<path d="m6.34 17.66-1.41 1.41"></path><path d="m19.07 4.93-1.41 1.41"></path>'
    "</svg>"
)

_MOON_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" '
    'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
    'stroke-linejoin="round" aria-hidden="true">'
    '<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"></path>'
    "</svg>"
)

_MONITOR_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" '
    'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
    'stroke-linejoin="round" aria-hidden="true">'
    '<rect width="20" height="14" x="2" y="3" rx="2"></rect>'
    '<line x1="8" x2="16" y1="21" y2="21"></line>'
    '<line x1="12" x2="12" y1="17" y2="21"></line>'
    "</svg>"
)


@define_component()
def ThemeToggle(_: ComponentContext[None]):
    signal, controller = use_theme()

    label = use_computed(
        lambda: {
            Theme.LIGHT: "Theme: Light (click to switch to dark)",
            Theme.DARK: "Theme: Dark (click to switch to system)",
            Theme.SYSTEM: "Theme: System (click to switch to light)",
        }[signal.value]
    )

    icon = use_computed(
        lambda: {
            Theme.LIGHT: _SUN_SVG,
            Theme.DARK: _MOON_SVG,
            Theme.SYSTEM: _MONITOR_SVG,
        }[signal.value]
    )

    return html.BUTTON(
        {
            "type": "button",
            "class": "theme-toggle",
            "aria-label": label,
            "title": label,
            "@click": lambda _ev: controller.cycle(),
        },
        raw_html(icon, wrapper="span"),
    )


ThemeToggle.scoped_style = {
    ".theme-toggle": {
        "display": "inline-flex",
        "align-items": "center",
        "justify-content": "center",
        "width": "2.25rem",
        "height": "2.25rem",
        "padding": "0",
        "line-height": "1",
        "background-color": "transparent",
        "color": "var(--color-fg)",
        "border": "1px solid var(--color-border)",
        "border-radius": "var(--radius-sm)",
        "cursor": "pointer",
        "transition": "background-color 0.15s ease, color 0.15s ease",
    },
    ".theme-toggle > span": {
        "display": "inline-flex",
        "align-items": "center",
        "justify-content": "center",
    },
    ".theme-toggle svg": {
        "display": "block",
    },
    ".theme-toggle:hover": {
        "background-color": "var(--color-bg-elevated)",
    },
    ".theme-toggle:focus-visible": {
        "outline": "2px solid var(--color-accent)",
        "outline-offset": "2px",
    },
}
