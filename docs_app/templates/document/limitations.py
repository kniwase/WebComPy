from webcompy.components import ComponentContext, define_component
from webcompy.elements import html


@define_component
def DocumentLimitations(_: ComponentContext[None]):
    return html.DIV(
        {"class": "page-container"},
        html.H1({}, "Template Engine Limitations"),
        html.P(
            {},
            "This page documents intentional limitations of the WebComPy template engine and Markdown processor. These constraints exist for security, predictability, or implementation simplicity.",
        ),
        html.H2({}, "Expression Language"),
        html.P(
            {},
            "The {{ }} expression language supports only variable paths with dot notation. The following are NOT supported:",
        ),
        html.UL(
            {},
            html.LI({}, "Subscript expressions: {{ items[0] }}"),
            html.LI({}, "Function calls: {{ items.length() }}"),
            html.LI({}, "Filters: {{ name | upper }}"),
            html.LI({}, "Arithmetic: {{ count + 1 }}"),
        ),
        html.P(
            {},
            "Only dotted variable paths like {{ user.name }} are allowed. Attempting unsupported expressions raises an error at template rendering time.",
        ),
        html.H2({}, "Template Comments"),
        html.P({}, "The syntax {# ... #} is NOT supported. There is no comment syntax in WebComPy templates."),
        html.H2({}, "Escaping Literal {{ in Templates"),
        html.P(
            {},
            "There is no mechanism to escape literal double-braces. If you need {{ }} in rendered output, structure your content to avoid the pattern.",
        ),
        html.H2({}, "Scoped CSS Limits"),
        html.P(
            {},
            "The scoped CSS system uses data attributes to scope styles to components. At-rules are handled as follows:",
        ),
        html.UL(
            {},
            html.LI({}, "@media, @supports, @container, @keyframes ARE supported"),
            html.LI({}, "These at-rules do NOT receive the scoping attribute selector"),
            html.LI({}, "Each component's scoped CSS is injected as a separate style element"),
        ),
        html.H2({}, "Markdown Processor"),
        html.H3({}, "Supported GFM Features"),
        html.P({}, "The Markdown processor implements the GitHub Flavored Markdown specification, including:"),
        html.UL(
            {},
            html.LI({}, "Headings (ATX and setext)"),
            html.LI({}, "Paragraphs with hard and soft line breaks"),
            html.LI({}, "Fenced and indented code blocks"),
            html.LI({}, "Block quotes, lists (ordered and unordered), nested lists"),
            html.LI({}, "Thematic breaks (horizontal rules)"),
            html.LI({}, "HTML blocks (types 1-7)"),
            html.LI({}, "Link reference definitions"),
            html.LI({}, "GFM tables"),
            html.LI({}, "GFM task list items"),
            html.LI({}, "Emphasis, strong, strikethrough"),
            html.LI({}, "Code spans"),
            html.LI({}, "Backslash escapes and character/numeric entity references"),
            html.LI({}, "Links and images (inline, reference, shortcut forms)"),
            html.LI({}, "Autolinks (angle-bracket and extended GFM forms)"),
            html.LI({}, "Raw inline HTML (with GFM tagfilter for disallowed tags)"),
        ),
        html.H3({}, "Non-GFM Non-Goals"),
        html.P({}, "The following extensions are intentionally NOT implemented:"),
        html.UL(
            {},
            html.LI({}, "Footnotes"),
            html.LI({}, "Definition lists"),
            html.LI({}, "Heading anchors / auto-generated IDs"),
            html.LI({}, "Math notation"),
            html.LI({}, "Custom containers"),
        ),
        html.H3({}, "URL Scheme Security"),
        html.P(
            {},
            "For inline links, reference links, and images, only the following schemes are permitted: http, https, mailto, relative URLs, and fragment identifiers (#). All other schemes render as literal text without a link element.",
        ),
        html.P(
            {},
            "Autolinks (angle-bracket and GFM extended forms) apply a deny-list instead: only javascript:, data:, and vbscript: are rejected; any other valid scheme produces a link.",
        ),
        html.H2({}, "HTML Parsing"),
        html.P({}, "The HTML parser used for component tags and attributes has the following limitations:"),
        html.UL(
            {},
            html.LI(
                {},
                "Tag and attribute names are case-normalized to lowercase, breaking case-sensitive SVG element and attribute names (e.g., viewBox, linearGradient)",
            ),
            html.LI(
                {}, "HTML entities decoded by the parser (e.g., &#123;) become live {{ }} holes in template context"
            ),
        ),
    )
