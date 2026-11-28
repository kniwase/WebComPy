from webcompy.components import ComponentContext, define_component
from webcompy.router import RouterContext
from webcompy.template import load_markdown_document

from ...components.demo_display import DemoDisplay
from ...components.docs_page import docs_page_template


@define_component()
async def GuidesStep4FormsPage(context: ComponentContext[RouterContext]):
    doc = await load_markdown_document(
        "documents/guides_step4_forms.md", copyable_code_blocks=True, heading_anchors=True
    )
    context.set_title(f"{doc.metadata['title']} - WebComPy Docs")
    return docs_page_template(
        doc,
        context.props.path,
        extra_content=DemoDisplay(
            {
                "title": "Step 4 Live Demo",
                "app_name": "todo_tutorial/step4",
                "demo_path": "/_demos/todo_tutorial/step4/app.py",
            }
        ),
    )
