from __future__ import annotations

import json
import os

from webcompy.app import WebComPyApp, WebComPyAppConfig
from webcompy.components._generator import define_component
from webcompy.elements import html


@define_component("loading-app-home")
def LoadingAppHome(context):
    return html.DIV(
        {},
        html.P({"data-testid": "loading-root"}, "Loading App"),
        html.A({"href": "/other", "data-testid": "nav-link"}, "Go"),
        html.BUTTON({"data-testid": "load-btn"}, "Click"),
    )


_loading = json.loads(os.environ.get("LOADING_JSON", "null"))
app = WebComPyApp(root_component=LoadingAppHome, config=WebComPyAppConfig(loading=_loading))
