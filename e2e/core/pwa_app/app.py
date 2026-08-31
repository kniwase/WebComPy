import os

from webcompy.app import WebComPyApp, WebComPyAppConfig
from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.router import Router, RouterContext, RouterView

base_url = os.environ.get("PWA_BASE_URL", "/")


@define_component()
def PwaAppRoot(context):
    return html.DIV({"data-testid": "pwa-app"}, RouterView())


@define_component()
def PwaHomePage(context: ComponentContext[RouterContext]):
    context.set_title("Home - PWA E2E")
    return html.DIV({"data-testid": "home-page"}, html.H1({}, "PWA Home Page"))


@define_component()
def PwaAboutPage(context: ComponentContext[RouterContext]):
    context.set_title("About - PWA E2E")
    return html.DIV({"data-testid": "about-page"}, html.H1({}, "PWA About Page"))


@define_component()
def PwaNotFound(context: ComponentContext[RouterContext]):
    context.set_title("Not Found - PWA E2E")
    return html.DIV({"data-testid": "not-found"}, html.H3({}, "Not Found"))


router = Router(
    {"path": "/", "component": PwaHomePage},
    {"path": "/about", "component": PwaAboutPage},
    default=PwaNotFound,
    mode="history",
)

app = WebComPyApp(root_component=PwaAppRoot, router=router, config=WebComPyAppConfig(base_url=base_url))
