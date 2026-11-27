from webcompy.components import ComponentContext, define_component
from webcompy.router import RouterContext
from webcompy.template import load_markdown_document

from ...components.docs_page import examples_page_template


@define_component()
async def ExampleTeleportPage(context: ComponentContext[RouterContext]):
    doc = await load_markdown_document("documents/example_teleport.md", copyable_code_blocks=True, heading_anchors=True)
    context.set_title(f"{doc.metadata['title']} - WebComPy Docs")
    return examples_page_template(doc, context.props.path, demo_app="teleport")
