from __future__ import annotations

import json
import os

from webcompy.app import WebComPyApp, WebComPyAppConfig
from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.router import Router, RouterView


@define_component("loading-app-home")
def LoadingAppHome(context):
    return html.DIV(
        {},
        html.P({"data-testid": "loading-root"}, "Loading App"),
        html.A({"href": "/other", "data-testid": "nav-link"}, "Go"),
        html.BUTTON({"data-testid": "load-btn"}, "Click"),
    )


@define_component("loading-app-other")
def LoadingAppOther(context):
    return html.DIV({}, html.P({"data-testid": "loading-other"}, "Other"))


@define_component("loading-app-root")
def LoadingAppRoot(_: ComponentContext[None]):
    return html.DIV({}, RouterView())


router = Router(
    {"path": "/", "component": LoadingAppHome},
    {"path": "/other", "component": LoadingAppOther},
    mode="history",
)

_loading = json.loads(os.environ.get("LOADING_JSON", "null"))
app = WebComPyApp(root_component=LoadingAppRoot, router=router, config=WebComPyAppConfig(loading=_loading))
