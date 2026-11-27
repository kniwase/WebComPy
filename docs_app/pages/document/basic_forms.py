from webcompy.components import ComponentContext, define_component
from webcompy.router import RouterContext
from webcompy.template import load_markdown_document

from ...components.docs_page import docs_page_template


@define_component()
async def BasicFormsPage(context: ComponentContext[RouterContext]):
    doc = await load_markdown_document("documents/basic_forms.md", copyable_code_blocks=True, heading_anchors=True)
    context.set_title(f"{doc.metadata['title']} - WebComPy Docs")
    return docs_page_template(doc, context.props.path)
