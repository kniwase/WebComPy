from __future__ import annotations

from webcompy.app import WebComPyApp, WebComPyAppConfig
from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.router import Router, RouterView, lazy


@define_component()
def ProfileAppHome(context):
    return html.DIV({}, html.P({"data-testid": "profile-root"}, "Profile App"))


@define_component()
def ProfileAppLazy(context):
    return html.DIV({}, html.P({"data-testid": "profile-lazy"}, "Lazy Page"))


@define_component()
def ProfileAppRoot(_: ComponentContext[None]):
    return html.DIV({}, RouterView())


router = Router(
    {"path": "/", "component": ProfileAppHome},
    {"path": "/lazy", "component": lazy("profile_app.app:ProfileAppLazy", __file__)},
    mode="history",
)

app = WebComPyApp(root_component=ProfileAppRoot, router=router, config=WebComPyAppConfig(profile=True))
