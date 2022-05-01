try:
    from browser import DOMNode, DOMEvent  # type: ignore
except ModuleNotFoundError:
    from webcompy.exception import WebComPyException

    def raise_exception(name: str):
        raise WebComPyException(
            f"{name} object can be accessed only in browser environment."
        )

    class DOMNode:
        def __init__(self, *args, **kwargs) -> None:  # type: ignore
            raise_exception("DOMNode")

        @classmethod
        def __getattr__(cls, _):
            raise_exception("DOMNode")

    class DOMEvent:
        def __init__(self, *args, **kwargs) -> None:  # type: ignore
            raise_exception("DOMEvent")

        @classmethod
        def __getattr__(cls, _):
            raise_exception("DOMEvent")
