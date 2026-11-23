from webcompy.components import ComponentContext, define_component
from webcompy.router import RouterContext
from webcompy.template import load_markdown_document

from ...components.docs_page import DOCS_PAGE_SCOPED_STYLE, docs_page_template


@define_component()
async def GuidesOverviewPage(context: ComponentContext[RouterContext]):
    doc = await load_markdown_document("documents/guides_overview.md")
    context.set_title(f"{doc.metadata['title']} - WebComPy Docs")
    return docs_page_template(doc, context.props.path)


GuidesOverviewPage.scoped_style = DOCS_PAGE_SCOPED_STYLE
