from __future__ import annotations

from dataclasses import dataclass

from webcompy.app import WebComPyApp
from webcompy.components import define_component
from webcompy.elements import html
from webcompy.rpc import Procedure


@dataclass
class AddParams:
    a: int


def _add(p: AddParams) -> int:
    return p.a


def test_mount_present_when_bound():

    @define_component("test-root")
    def TestRoot(ctx):
        return html.DIV({})

    app = WebComPyApp(root_component=TestRoot)
    add = Procedure("add", AddParams, int)
    app.rpc.bind(add, _add)
    # check registry has procedures
    assert app.rpc.has_procedures is True
    assert app.rpc.get("add") is not None


def test_mount_absent_when_no_procedures():
    from webcompy.app import WebComPyApp
    from webcompy.components import define_component
    from webcompy.elements import html

    @define_component("test-root2")
    def TestRoot2(ctx):
        return html.DIV({})

    app = WebComPyApp(root_component=TestRoot2)
    assert app.rpc.has_procedures is False
