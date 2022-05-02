from functools import partial
from itertools import chain
from typing import Any, Callable, List, TypeVar
from webcompy.reactive import ReactiveBase
from webcompy.elements.types._text import NewLine
from webcompy.elements.typealias._element_property import ElementChildren
from webcompy.exception import WebComPyException
from webcompy.elements.types._dynamic import DynamicElement
from webcompy.brython import browser


T = TypeVar("T")


class RepeatElement(DynamicElement):
    _index_map: list[tuple[Any, tuple[int, int]]]

    def __init__(
        self,
        sequence: ReactiveBase[List[T]],
        template: Callable[[T], ElementChildren],
    ) -> None:
        self._template = template
        self._sequence = sequence
        self._reactive_activated = False

        if not isinstance(self._sequence, ReactiveBase):  # type: ignore
            raise ValueError("Argument 'sequence' must be Reactive Object.")
        super().__init__()

    def _on_set_parent(self):
        if not browser:
            self._children = self._generate_children()

    def _generate_children(self):
        return list(
            filter(
                None,
                map(
                    partial(self._create_child_element, self._parent, None),
                    map(self._template, self._sequence.value),
                ),
            )
        )

    def _render(self):
        self._refresh()
        if not self._reactive_activated:
            self._reactive_activated = True
            self._set_callback_id(self._sequence.on_after_updating(self._refresh))

    def _refresh(self, *args: Any):
        parent_node = self._parent._get_node()
        if not parent_node:
            raise WebComPyException(
                f"'{self.__class__.__name__}' does not have its parent."
            )
        for _ in range(len(self._children)):
            self._children.pop(-1)._remove_element()
        self._children = self._generate_children()
        self._re_index_children(False)
        self._parent._re_index_children(False)
        for child in self._children:
            child._render()


class MultiLineTextElement(RepeatElement):
    _text: str | ReactiveBase[Any]

    def __init__(self, text: str | ReactiveBase[Any]) -> None:
        self._text = text
        super(RepeatElement, self).__init__()

    def _generate_children(self):
        if isinstance(self._text, str):
            lines = self._text.split("\n")
        else:
            lines = str(self._text.value).split("\n")
        return list(
            filter(
                None,
                map(
                    partial(self._create_child_element, self._parent, None),
                    chain.from_iterable(
                        zip(
                            lines,
                            map(lambda _: NewLine(), lines),
                        )
                    ),
                ),
            )
        )[:-1]

    def _render(self):
        self._refresh()
        if isinstance(self._text, ReactiveBase):
            self._set_callback_id(self._text.on_after_updating(self._refresh))
