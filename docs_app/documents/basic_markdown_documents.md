---
title: Markdown Documents
description: Render Markdown strings with render_markdown(), load frontmatter-backed documents with load_markdown_document(), extract TOC headings, and apply prose.css.
---

# Markdown Documents

WebComPy includes built-in CommonMark-compatible Markdown rendering and document loading under `webcompy.template`. You can turn inline Markdown strings into reactive `Element` trees or build full multi-page documentation sites with frontmatter metadata, table-of-contents extraction, syntax-highlighted code blocks, and the opt-in `.prose` typography stylesheet.

## At a glance

Load a `.md` resource from your app package inside an `async def` component setup:

```python
from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.router import RouterContext
from webcompy.template import load_markdown_document


@define_component()
async def GuidePage(context: ComponentContext[RouterContext]):
    doc = await load_markdown_document("documents/intro.md")
    context.set_title(f"{doc.metadata['title']} - My App")
    return html.ARTICLE({"class": "prose"}, doc.content)
```

## Inline rendering vs document loading

WebComPy exposes two complementary entry points in `webcompy.template`:

| API | Sync / Async | Default transforms | Returns |
|---|---|---|---|
| `render_markdown(source, context=None, *, heading_ids=False, code_blocks=False, classes=None)` | Synchronous | Plain CommonMark baseline (`heading_ids=False`, `code_blocks=False`) | `ElementAbstract` |
| `load_markdown_document(source, *, heading_ids=True, code_blocks=True, classes=None, context=None)` | Async (`await`) | Documentation defaults (`heading_ids=True`, `code_blocks=True`) | `MarkdownDocument` |

Use `render_markdown()` when you already have a Markdown string in memory:

```python
from webcompy.template import render_markdown

card_body = render_markdown(
    "Hello **{{ user }}**! Check the [guide](/documents/getting-started/quickstart).",
    context={"user": user_signal},
    heading_ids=True,
    code_blocks=True,
)
```

Passing `context=` enables the same safe `{{ ... }}` interpolation inside Markdown text paragraphs, headings, and inline markup. Pass `classes={"table": "data-table"}` to attach extra CSS classes by tag name.

Use `load_markdown_document()` when loading a resource file via `ResourcePort`. Because it reads through the framework's resource abstraction, SSR/SSG pre-rendering records the file contents for browser hydration so the client does not re-fetch the Markdown file on startup.

## Frontmatter formats

`load_markdown_document()` parses an optional frontmatter header at the very top of the file and stores it on `doc.metadata`:

- **Flat key-value (`---`)**: lightweight `key: value` string pairs (whitespace trimmed). Malformed lines without `:` raise `WebComPyException`.

  ```markdown
  ---
  title: Getting Started
  description: How to configure your project.
  ---

  # Getting Started
  ```

- **TOML (`+++`)**: delimited by three plus signs (`+++`) and parsed with stdlib `tomllib`, supporting nested tables, integers, booleans, and arrays.

  ```markdown
  +++
  title = "Getting Started"
  order = 1

  [author]
  name = "Alice"
  +++

  # Getting Started
  ```

## `MarkdownDocument` and table of contents (`toc`)

`load_markdown_document()` returns an immutable `MarkdownDocument` with three fields:

- `doc.content`: the rendered `ElementAbstract` tree (with slug `id` attributes injected onto `<h1>`–`<h6>` headings when `heading_ids=True`).
- `doc.metadata`: `Mapping[str, Any]` parsed from frontmatter (`{}` if none).
- `doc.toc`: a `tuple[HeadingInfo, ...]` of headings collected in document order, each carrying `.level` (`1`–`6`), `.text`, and matching `.id`.

Build a table-of-contents sidebar directly from `doc.toc`:

```python
html.UL(
    {"class": "toc"},
    *(
        html.LI(
            {"class": f"toc-level-{h.level}"},
            html.A({"href": f"{context.props.path}#{h.id}"}, h.text),
        )
        for h in doc.toc
    ),
)
```

## Opt-in typography with `prose.css`

WebComPy ships a typography stylesheet at `/_webcompy-ui/prose.css` (not loaded by default in `index.css`). Register it in your app's head links and wrap rendered Markdown in `class="prose"`:

```python
app.set_head(
    {
        "title": "My Docs",
        "link": [
            {"rel": "stylesheet", "href": "/_webcompy-ui/prose.css"},
        ],
    }
)
```

`prose.css` lives in `@layer prose` and consumes theme tokens (`--color-*`, `--space-*`, `--font-*`), so headings, lists, blockquotes, tables, and `CodeBlock` spacing follow light and dark modes automatically while leaving non-`.prose` elements untouched.

## Authoring docs pages for your own app

Putting these pieces together is how WebComPy's own documentation site works:

1. Place `.md` files under a resource directory (such as `app/documents/`) and include it in your package resources or `static` assets.
2. Add `<link rel="stylesheet" href="/_webcompy-ui/prose.css">` via `app.set_head(...)`.
3. Create thin `async def` page components calling `await load_markdown_document(...)`, calling `context.set_title(doc.metadata["title"])`, and rendering `<article class="prose">` plus `doc.toc`.
4. Wire those page components into your `Router` (and read [Routing](/documents/basic/routing) to connect links and URL paths).

## Notes & caveats

- `render_markdown()` sets `code_blocks=False` and `heading_ids=False` by default so inline Markdown rendering stays lightweight; opt in with keyword arguments when you want syntax highlighting or anchor IDs.
- Always use `load_markdown_document()` inside `async def` component setup so static site generation (SSG) and SSR capture both `<title>` metadata and the resource hydration payload before HTML emission.

## Next steps

- Wire Markdown pages into multi-page navigation in [Routing](/documents/basic/routing).
- Customize theme colors and cascade layers in [Styling & Themes](/documents/basic/styling-and-themes).
