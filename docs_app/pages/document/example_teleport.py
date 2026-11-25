from webcompy.components import ComponentContext, define_component
from webcompy.router import RouterContext
from webcompy.template import load_markdown_document

from ...components.docs_page import DOCS_PAGE_SCOPED_STYLE, examples_page_template


@define_component()
async def ExampleTeleportPage(context: ComponentContext[RouterContext]):
    doc = await load_markdown_document("documents/example_teleport.md")
    context.set_title(f"{doc.metadata['title']} - WebComPy Docs")
    return examples_page_template(doc, context.props.path, demo_app="teleport")


ExampleTeleportPage.scoped_style = DOCS_PAGE_SCOPED_STYLE
