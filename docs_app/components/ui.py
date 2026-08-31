from typing import TypedDict

from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.ui import Card


class InlineCodeProps(TypedDict, total=False):
    text: str


@define_component()
def InlineCode(context: ComponentContext[InlineCodeProps]):
    return html.CODE(
        {"class": "ui-inline-code"},
        context.props.get("text", ""),
    )


class CardProps(TypedDict, total=False):
    title: str


@define_component()
def DocsCard(context: ComponentContext[CardProps]):
    body = context.slots("default")
    title = context.props.get("title")
    slots: dict = {"default": lambda: body}
    if title:
        slots["header"] = lambda: title
    return Card({"class_name": "ui-card"}, slots=slots)


class SectionProps(TypedDict, total=False):
    heading: str


@define_component()
def DocsSection(context: ComponentContext[SectionProps]):
    return html.SECTION(
        {"class": "ui-section"},
        html.H3({"class": "ui-section-heading"}, context.props.get("heading", "")),
        html.DIV({"class": "ui-section-body"}, context.slots("default")),
    )


class LinkProps(TypedDict, total=False):
    href: str
    text: str


@define_component()
def DocsLink(context: ComponentContext[LinkProps]):
    return html.A(
        {"class": "ui-link", "href": context.props.get("href", "#")},
        context.props.get("text", ""),
    )


class ButtonProps(TypedDict, total=False):
    text: str
    href: str
    variant: str
    aria_label: str
    role: str
    aria_checked: str
    aria_expanded: str
    aria_controls: str
    type: str
    onclick: object


@define_component()
def DocsButton(context: ComponentContext[ButtonProps]):
    props = context.props
    variant = props.get("variant", "default")
    classes = "ui-button" + (f" ui-button-{variant}" if variant != "default" else "")

    attrs: dict = {"class": classes, "type": props.get("type", "button")}

    if "href" in props:
        attrs["href"] = props["href"]
    if "aria_label" in props:
        attrs["aria-label"] = props["aria_label"]
    if "role" in props:
        attrs["role"] = props["role"]
    if "aria_checked" in props:
        attrs["aria-checked"] = props["aria_checked"]
    if "aria_expanded" in props:
        attrs["aria-expanded"] = props["aria_expanded"]
    if "aria_controls" in props:
        attrs["aria-controls"] = props["aria_controls"]
    if "onclick" in props:
        attrs["@click"] = props["onclick"]

    tag = html.A if "href" in props else html.BUTTON
    return tag(
        attrs,
        props.get("text", ""),
    )


InlineCode.scoped_style = {
    ".ui-inline-code": {
        "font-family": "var(--font-mono)",
        "font-size": "0.9em",
        "padding": "0.15em 0.4em",
        "background-color": "var(--color-bg-code)",
        "border": "1px solid var(--color-border)",
        "border-radius": "var(--radius-sm)",
        "color": "var(--color-fg)",
    },
}

DocsCard.scoped_style = {
    ".ui-card": {
        "margin": "var(--space-5) 0",
    },
}

DocsSection.scoped_style = {
    ".ui-section": {
        "margin": "var(--space-5) auto",
        "padding": "var(--space-4) var(--space-5)",
        "background-color": "var(--color-bg-card)",
        "border": "1px solid var(--color-border)",
        "border-radius": "var(--radius-md)",
    },
    ".ui-section-heading": {
        "padding-bottom": "var(--space-2)",
        "border-bottom": "2px solid var(--color-accent)",
        "font-size": "var(--font-size-xl)",
        "font-weight": "600",
        "color": "var(--color-fg)",
        "margin-top": "0",
    },
    ".ui-section-body": {
        "margin-top": "var(--space-3)",
        "color": "var(--color-fg)",
    },
}

DocsLink.scoped_style = {
    ".ui-link": {
        "color": "var(--color-link)",
        "text-decoration": "none",
        "transition": "color 0.15s ease",
    },
    ".ui-link:hover": {
        "color": "var(--color-link-hover)",
        "text-decoration": "underline",
    },
}

DocsButton.scoped_style = {
    ".ui-button": {
        "display": "inline-block",
        "padding": "var(--space-2) var(--space-4)",
        "font-size": "var(--font-size-base)",
        "font-weight": "500",
        "font-family": "var(--font-sans)",
        "color": "var(--color-fg)",
        "background-color": "var(--color-bg-elevated)",
        "border": "1px solid var(--color-border)",
        "border-radius": "var(--radius-sm)",
        "cursor": "pointer",
        "text-decoration": "none",
        "text-align": "center",
        "line-height": "1.2",
        "transition": "background-color 0.15s ease, border-color 0.15s ease",
    },
    ".ui-button:hover": {
        "background-color": "var(--color-bg-card)",
        "border-color": "var(--color-accent)",
    },
    ".ui-button-primary": {
        "color": "#ffffff",
        "background-color": "var(--color-accent)",
        "border-color": "var(--color-accent)",
    },
    ".ui-button-primary:hover": {
        "background-color": "var(--color-link-hover)",
        "border-color": "var(--color-link-hover)",
    },
    ".ui-button-danger": {
        "color": "#ffffff",
        "background-color": "var(--color-danger)",
        "border-color": "var(--color-danger)",
    },
    ".ui-button-danger:hover": {
        "filter": "brightness(0.9)",
    },
}
