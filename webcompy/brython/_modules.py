from typing import Any, Callable, Type, Union, cast


class DOMNodeType:
    __webcompy_node__: bool

    @classmethod
    def __getattribute__(cls, _: str) -> Any:
        ...

    def bind(self, event_name: str, handler: Callable[["DOMEventType"], Any]):
        """The handler function is called when the event evt_name occurs on the element.

        Args:
            event_name (str)
            handler (Callable[[DOMEvent], Any])
        """
        ...

    def unbind(
        self,
        event_name: str,
        handler: Union[Callable[["DOMEventType"], Any], None] = None,
    ):
        """Removes the association of function handler to the event named evt_name.
        If handler is omitted, removes all the associations for the event.

        Args:
            event_name (str): _description_
            handler (Callable[[DOMEvent], Any], optional): Defaults to None.
        """
        ...

    def events(self, event_name: str) -> list[Callable[["DOMEventType"], Any]]:
        """Returns the list of functions that handle the event named evt_name.

        Args:
            event_name (str): _description_

        Returns:
            list[Callable[["DOMEventType"], Any]]
        """
        ...


class DOMEventType:
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
    def currentTarget(self) -> DOMNodeType:
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
    def target(self) -> DOMNodeType:
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


try:
    from browser import DOMNode, DOMEvent  # type: ignore

    DOMNode = cast(Type[DOMNodeType], DOMNode)
    DOMEvent = cast(Type[DOMEventType], DOMEvent)
except ModuleNotFoundError:
    DOMNode = DOMNodeType
    DOMEvent = DOMEventType


class HTMLBodyElement(DOMNode):
    @classmethod
    def __getattribute__(cls, _: str) -> Any:
        ...


class HTMLDocument(DOMNode):
    body: HTMLBodyElement

    def getElementById(self, element_id: str) -> DOMNode:
        """Returns a reference to the DOM element whose id is element_id.

        Args:
            _id (str)

        Returns:
            DOMNode
        """
        ...

    @classmethod
    def __getattribute__(cls, _: str) -> Any:
        ...


class BrythonJavascript:
    py2js: Callable[[str], str]
    NULL: Any
    UNDEFINED: Any
    this: Any
    JSON: Any
    Math: Any
    RegExp: Any
    String: Any


class BrythonBrowser:
    DOMNode: DOMNode
    DOMEvent: DOMEvent

    javascript: BrythonJavascript
    console: Any
    document: HTMLDocument
    local_storage: Any
    markdown: Any
    object_storage: Any
    session_storage: Any
    svg: Any
    timer: Any
    websocket: Any
    window: Any
    worker: Any

    def alert(self, message: str) -> None:
        """A function that prints the message in a pop-up window.

        Args:
            message (str)
        """
        ...

    def confirm(self, message: str) -> bool:
        """A function that prints the message in a window, and two buttons (ok/cancel).
        Returns True if ok, False if cancel.

        Args:
            message (str)

        Returns:
            bool
        """
        ...

    def prompt(self, message: str, default: str = "") -> str:
        """A function that prints the message in a window, and an entry field.
        Returns the entered value; if no value was entered, return default if defined, else the empty string.

        Args:
            message (str)
            default (str, optional): Defaults to "".

        Returns:
            str: the entered value
        """
        ...

    def load(self, script_url: str) -> None:
        """Load the Javascript library at address script_url.
        This function uses a blocking HttpClient call.
        It must be used when one can't load the Javascript library in the html page by <script src="prog.js"></script>.
        The names inserted by the library inside the global Javascript namespace are available
        in the Brython script as attributes of the window object.

        Args:
            script_url (str)
        """
        ...

    def run_script(self, src: str, name: str = ""):
        """this function executes the Python source code in src with an optional name.
        It can be used as an alternative to exec(),
        with the benefit that the indexedDB cache is used for importing modules from the standard library.

        Args:
            src (str): Python source code
        """

    def bind(
        self, target_element: DOMNodeType, event: Callable[[DOMEventType], None]
    ) -> None:
        """A function used as a decorator for event binding.

        Args:
            target_element (DOMNode)
            event (Callable[[DOMEvent], None])
        """

    def __getattr__(self, _: str) -> Any:
        ...


try:
    import browser  # type: ignore

    browser = cast(BrythonBrowser, browser)
except ModuleNotFoundError:
    browser = None


if browser:
    import javascript  # type: ignore
    from browser import (  # type: ignore
        local_storage,  # type: ignore
        markdown,  # type: ignore
        object_storage,  # type: ignore
        session_storage,  # type: ignore
        svg,  # type: ignore
        timer,  # type: ignore
        websocket,  # type: ignore
        worker,  # type: ignore
    )

    setattr(browser, "javascript", javascript)
    setattr(browser, "local_storage", local_storage)
    setattr(browser, "markdown", markdown)
    setattr(browser, "object_storage", object_storage)
    setattr(browser, "session_storage", session_storage)
    setattr(browser, "svg", svg)
    setattr(browser, "timer", timer)
    setattr(browser, "websocket", websocket)
    setattr(browser, "worker", worker)


browser = cast(BrythonBrowser | None, browser)
