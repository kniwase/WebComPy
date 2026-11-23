from webcompy.components import ComponentContext, define_component
from webcompy.router import RouterContext
from webcompy.template import load_markdown_document

from ...components.demo_display import DemoDisplay
from ...components.docs_page import DOCS_PAGE_SCOPED_STYLE, docs_page_template


@define_component()
async def GuidesStep5RemoteDataPage(context: ComponentContext[RouterContext]):
    doc = await load_markdown_document("documents/guides_step5_remote_data.md")
    context.set_title(f"{doc.metadata['title']} - WebComPy Docs")
    return docs_page_template(
        doc,
        context.props.path,
        extra_content=DemoDisplay(
            {
                "title": "Step 5 Live Demo",
                "app_name": "todo_tutorial/step5",
                "demo_path": "/_demos/todo_tutorial/step5/app.py",
            }
        ),
    )


GuidesStep5RemoteDataPage.scoped_style = DOCS_PAGE_SCOPED_STYLE
