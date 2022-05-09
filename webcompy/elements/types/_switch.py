from operator import truth
from typing import Any, Callable, List, Tuple, TypeAlias, cast
from webcompy.reactive._base import ReactiveBase
from webcompy.elements.types._abstract import ElementAbstract
from webcompy.elements.typealias._element_property import ElementChildren
from webcompy.exception import WebComPyException
from webcompy.elements.types._dynamic import DynamicElement
from webcompy._browser._modules import browser


NodeGenerator: TypeAlias = Callable[[], ElementChildren]
SwitchCasesReactive: TypeAlias = list[tuple[ReactiveBase[Any], NodeGenerator]]
SwitchCasesReactiveList: TypeAlias = ReactiveBase[list[tuple[Any, NodeGenerator]]]
SwitchCases: TypeAlias = SwitchCasesReactive | SwitchCasesReactiveList


class SwitchElement(DynamicElement):
    _rendered_idx: int | None

    def __init__(
        self,
        cases: SwitchCases,
        default: NodeGenerator | None,
    ) -> None:
        self._cases = cases
        self._default = default
        self._reactive_activated = False
        self._rendered_idx = None
        super().__init__()

    def _select_generator(self) -> tuple[int, Callable[[], ElementChildren]]:
        if isinstance(self._cases, ReactiveBase):
            cases = self._cases.value
        else:
            cases = self._cases
        for idx, (cond, generator) in enumerate(
            cast(List[Tuple[ReactiveBase[Any] | Any, NodeGenerator]], cases)
        ):
            if truth(cond.value if isinstance(cond, ReactiveBase) else cond):
                return (idx, generator)
        if self._default:
            return (-1, self._default)
        else:
            return (-1, lambda: None)

    def _generate_children(self, generator: NodeGenerator) -> list[ElementAbstract]:
        ele = self._create_child_element(self._parent, None, generator())
        return [ele] if ele is not None else []

    def _render(self):
        self._refresh()
        if not self._reactive_activated:
            self._reactive_activated = True
            if isinstance(self._cases, ReactiveBase):
                self._set_callback_id(self._cases.on_after_updating(self._refresh))
            else:
                for cond, _ in self._cases:
                    if isinstance(cond, ReactiveBase):  # type: ignore
                        self._set_callback_id(cond.on_after_updating(self._refresh))

    def _refresh(self, *args: Any):
        idx, generator = self._select_generator()
        if idx == self._rendered_idx:
            return
        parent_node = self._parent._get_node()
        if not parent_node:
            raise WebComPyException(
                f"'{self.__class__.__name__}' does not have its parent."
            )
        self._rendered_idx = idx
        for _ in range(len(self._children)):
            self._children.pop(-1)._remove_element()
        self._children = self._generate_children(generator)
        for c_idx, child in enumerate(self._children):
            child._node_idx = self._node_idx + c_idx
            child._render()
        self._parent._re_index_children(False)

    def _on_set_parent(self):
        if not browser:

            def refresh(*args: Any):
                idx, generator = self._select_generator()
                self._rendered_idx = idx
                self._children = self._generate_children(generator)

            refresh()

            if not self._reactive_activated:
                self._reactive_activated = True

                if isinstance(self._cases, ReactiveBase):
                    self._set_callback_id(self._cases.on_after_updating(refresh))
                else:
                    for cond, _ in self._cases:
                        if isinstance(cond, ReactiveBase):  # type: ignore
                            self._set_callback_id(cond.on_after_updating(refresh))
