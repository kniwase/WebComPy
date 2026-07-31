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
            "The {{ }} expression language supports a safe subset of Python expressions. The following constructs are supported:",
        ),
        html.UL(
            {},
            html.LI({}, "Arithmetic: {{ count + 1 }}, {{ a * b }}, {{ items | length }}"),
            html.LI({}, "Comparisons: {{ count > 3 }}, {{ name == 'Alice' }}"),
            html.LI({}, "Boolean logic: {{ a and b }}, {{ not visible }}"),
            html.LI({}, "Subscripts: {{ items[0] }}, {{ dict['key'] }}"),
            html.LI({}, "Attribute access: {{ user.name }}, {{ obj.method() }}"),
            html.LI({}, "Method calls: {{ name.upper() }}"),
            html.LI({}, "Filters via |: {{ name | upper }}, {{ items | join(', ') }}"),
            html.LI({}, "Ternary: {{ 'yes' if flag else 'no' }}"),
            html.LI({}, "List/dict/set literals: {{ [1, 2, 3] }}, {{ {'a': 1} }}"),
        ),
        html.P({}, "The following constructs are intentionally NOT supported:"),
        html.UL(
            {},
            html.LI({}, "Comprehensions, lambda, walrus/assignment expressions"),
            html.LI({}, "F-strings, generator expressions"),
            html.LI({}, "Jinja2 tests (is defined, is none)"),
            html.LI({}, "Custom filter registration (registry is built-in)"),
            html.LI({}, "Dunder/private attribute access (names starting with _)"),
        ),
        html.P(
            {},
            "Signal-referencing expressions are automatically re-evaluated when the underlying Signal changes. Filters are only available via the pipe syntax (e.g., {{ name | upper }}), not as direct function calls ({{ upper(name) }}). Filter names take precedence over context variables on the right of |. Method calls from templates can mutate state (same exposure as Jinja2).",
        ),
        html.H2({}, "Template Comments"),
        html.P(
            {},
            "The syntax {# ... #} is supported. Template comments are stripped at compile time and do not appear in the rendered output.",
        ),
        html.P(
            {},
            "Inside {% raw %} blocks, {# and #} are preserved as literal text. Inside Markdown code blocks and code spans, template syntax (including comments) is automatically protected and rendered literally.",
        ),
        html.P(
            {},
            "Note: {# ... #} spans inside Markdown raw-HTML blocks (type 1) are also stripped. This matches Jinja2 behavior.",
        ),
        html.H2({}, "Escaping Literal {{ in Templates"),
        html.P(
            {},
            "Use {% raw %}...{% endraw %} to emit literal {{ }} or {% %} syntax in rendered output. For example: {% raw %}{{ not_a_var }}{% endraw %} renders as the literal string {{ not_a_var }}.",
        ),
        html.P(
            {},
            "HTML entities decoded by the HTML parser (e.g., &#123;) become live {{ }} holes in template context. Use {% raw %} for literal brace output.",
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
        html.H3({}, "Disallowed Raw HTML (tagfilter)"),
        html.P(
            {},
            "The GFM tagfilter extension escapes the leading < of disallowed tags (title, textarea, style, xmp, iframe, noembed, noframes, script, plaintext) when they appear as inline HTML or as HTML blocks of types 2-7.",
        ),
        html.P(
            {},
            "HTML blocks of type 1 (script, pre, style, textarea raw-text containers) pass through verbatim, because the GFM spec suite pins verbatim output for those examples. The template binding layer additionally rejects script, style, iframe, noembed, noframes, and xmp at render time; however textarea, title, and plaintext type-1 blocks are not rejected and flow into the DOM. For untrusted Markdown, apply a downstream HTML sanitizer.",
        ),
        html.H2({}, "HTML Parsing"),
        html.P({}, "The HTML parser used for component tags and attributes has the following limitations:"),
        html.UL(
            {},
            html.LI(
                {},
                "Tag and attribute names are case-normalized to lowercase, breaking case-sensitive SVG element and attribute names (e.g., viewBox, linearGradient). Use raw_html() for SVG content.",
            ),
            html.LI(
                {},
                "HTML entities decoded by the parser (e.g., &#123;) become live {{ }} holes in template context. Use {% raw %} for literal brace output.",
            ),
        ),
    )
