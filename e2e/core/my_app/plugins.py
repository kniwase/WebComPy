from webcompy.app import PluginScript
from webcompy.plugin import WebComPyPlugin


class ErudaPlugin(WebComPyPlugin):
    name = "eruda"

    @staticmethod
    def get_scripts() -> list[PluginScript]:
        return [
            PluginScript(
                attrs={
                    "type": "text/javascript",
                    "src": "https://cdnjs.cloudflare.com/ajax/libs/eruda/2.4.1/eruda.min.js",
                },
                script="eruda.init();",
                in_head=True,
                condition="new URLSearchParams(location.search).get('debug') === 'True'",
            ),
        ]
