from typing import Any, Callable, Type
from webcompy.elements._dom_objs import DOMNode, DOMEvent

class BrythonBrowserModule:
    class javascript:
        py2js: Callable[[str], str]
        NULL: Any
        UNDEFINED: Any
        this: Any
        JSON: Any
        Math: Any
        RegExp: Any
        String: Any
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
    def prompt(self, message: str, default: str = ...) -> str:
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
    def run_script(self, src: str, name: str = ...) -> None:
        """this function executes the Python source code in src with an optional name.
        It can be used as an alternative to exec(),
        with the benefit that the indexedDB cache is used for importing modules from the standard library.

        Args:
            src (str): Python source code
        """
    def bind(
        self, target_element: "DOMNode", event: Callable[["DOMEvent"], None]
    ) -> None:
        """A function used as a decorator for event binding.

        Args:
            target_element (DOMNode)
            event (Callable[[DOMEvent], None])
        """
    def __getattr__(self, _: str) -> Any: ...
    console: Any
    document: DOMNode
    local_storage: Any
    markdown: Any
    object_storage: Any
    session_storage: Any
    svg: Any
    timer: Any
    websocket: Any
    window: Any
    worker: Any
    DOMNode: Type[DOMNode]
    DOMEvent: Type[DOMEvent]

browser: BrythonBrowserModule | None
