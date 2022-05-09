from webcompy.elements._dom_objs import DOMNode
from webcompy.exception import WebComPyException


class DomNodeRef:
    _node: DOMNode | None

    def __init__(self) -> None:
        self._node = None

    @property
    def node(self) -> DOMNode:
        if self._node is None:
            raise WebComPyException("DomNodeRef is not initialized yet.")
        return self._node

    def __init_node__(self, node: DOMNode):
        self._node = node

    def __reset_node__(self):
        self._node = None
