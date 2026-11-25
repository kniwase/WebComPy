from webcompy.components import ComponentContext, define_component
from webcompy.router import RouterContext
from webcompy.template import load_markdown_document

from ...components.docs_page import DOCS_PAGE_SCOPED_STYLE, docs_page_template_with_demo


@define_component()
async def MigrationFromJinja2FastapiPage(context: ComponentContext[RouterContext]):
    doc = await load_markdown_document("documents/migration_from_jinja2_fastapi.md")
    context.set_title(f"{doc.metadata['title']} - WebComPy Docs")
    return docs_page_template_with_demo(
        doc,
        context.props.path,
        demo_app="migration_users",
        demo_title="WebComPy Live Demo — Team Directory",
        before_heading_id="why-each-line-changed",
    )


MigrationFromJinja2FastapiPage.scoped_style = DOCS_PAGE_SCOPED_STYLE
