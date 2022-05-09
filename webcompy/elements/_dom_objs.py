from typing import Any, Callable, Protocol, Union


class DOMNode(Protocol):
    __webcompy_node__: bool

    def __getattr__(self, name: str) -> Any:
        ...

    def __setattr__(self, name: str, obj: Any) -> Any:
        ...

    def bind(self, event_name: str, handler: Callable[["DOMEvent"], Any]) -> None:
        """The handler function is called when the event evt_name occurs on the element.

        Args:
            event_name (str)
            handler (Callable[[DOMEvent], Any])
        """
        ...

    def unbind(
        self,
        event_name: str,
        handler: Union[Callable[["DOMEvent"], Any], None] = ...,
    ) -> None:
        """Removes the association of function handler to the event named evt_name.
        If handler is omitted, removes all the associations for the event.

        Args:
            event_name (str): _description_
            handler (Callable[[DOMEvent], Any], optional): Defaults to None.
        """
        ...

    def events(self, event_name: str) -> list[Callable[["DOMEvent"], Any]]:
        """Returns the list of functions that handle the event named evt_name.

        Args:
            event_name (str): _description_

        Returns:
            list[Callable[["DOMEvent"], Any]]
        """
        ...


class DOMEvent(Protocol):
    def __getattr__(self, _: str) -> Any:
        ...

    @property
    def bubbles(self) -> bool:
        """indicates whether the given event bubbles up through the DOM or not"""
        ...

    @property
    def cancelable(self) -> bool:
        """indicates whether the event is cancelable or not"""
        ...

    @property
    def currentTarget(self) -> DOMNode:
        """identifies the current target for the event, as the event traverses the DOM.
        It always refers to the element the event handler has been attached to as opposed to
        event.target which identifies the element on which the event occurred."""
        ...

    @property
    def defaultPrevented(self) -> bool:
        """indicating whether or not event.preventDefault() was called on the event"""
        ...

    @property
    def eventPhase(self) -> int:
        """indicates which phase of the event flow is currently being evaluated"""
        ...

    @property
    def target(self) -> DOMNode:
        """the object the event was dispatched on.
        It is different from event.currentTarget
        when the event handler is called in bubbling or capturing phase of the event"""
        ...

    @property
    def timeStamp(self) -> int:
        """the time (in milliseconds from the beginning of the current document's lifetime)
        at which the event was created"""
        ...

    @property
    def type(self) -> str:
        """contains the event type"""
        ...

    def preventDefault(self) -> None:
        """prevents the execution of the action associated by default to the event."""
        ...

    def stopPropagation(self) -> None:
        """prevents further propagation of the current event."""
        ...
