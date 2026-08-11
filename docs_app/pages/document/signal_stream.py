from webcompy.components import ComponentContext, define_component
from webcompy.router import RouterContext
from webcompy.template import load_markdown_document

from ...components.docs_page import DOCS_PAGE_SCOPED_STYLE, docs_page_template


@define_component
async def SignalStreamPage(context: ComponentContext[RouterContext]):
    doc = await load_markdown_document("documents/signal_stream.md")
    context.set_title(f"{doc.metadata['title']} - WebComPy Docs")
    return docs_page_template(doc, context.props.path)


SignalStreamPage.scoped_style = DOCS_PAGE_SCOPED_STYLE
