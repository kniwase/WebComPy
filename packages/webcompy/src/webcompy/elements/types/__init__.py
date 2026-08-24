"""Element node classes backing the generator functions."""

from webcompy.elements.types._abstract import ElementAbstract
from webcompy.elements.types._client_only import ClientOnlyElement
from webcompy.elements.types._element import Element
from webcompy.elements.types._error_boundary import ErrorBoundaryElement
from webcompy.elements.types._fragment import FragmentElement
from webcompy.elements.types._repeat import MultiLineTextElement, RepeatElement
from webcompy.elements.types._suspense import SuspenseElement
from webcompy.elements.types._switch import SwitchCases, SwitchElement
from webcompy.elements.types._teleport import TeleportElement
from webcompy.elements.types._text import NewLine, TextElement
from webcompy.elements.types._transition import TransitionElement

__all__ = [
    "ClientOnlyElement",
    "Element",
    "ElementAbstract",
    "ErrorBoundaryElement",
    "FragmentElement",
    "MultiLineTextElement",
    "NewLine",
    "RepeatElement",
    "SuspenseElement",
    "SwitchCases",
    "SwitchElement",
    "TeleportElement",
    "TextElement",
    "TransitionElement",
]
