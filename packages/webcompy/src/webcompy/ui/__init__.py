"""First-party UI toolkit: theme system, code blocks, and UI primitives.

The themed components are re-exported as the default convenient path;
the headless variants stay under :mod:`webcompy.ui.headless` for
full design control.
"""

from webcompy.ui import code_block as code_block
from webcompy.ui import components as components
from webcompy.ui import headless as headless
from webcompy.ui import theme as theme
from webcompy.ui.components import Accordion as Accordion
from webcompy.ui.components import Collapse as Collapse
from webcompy.ui.components import Drawer as Drawer
from webcompy.ui.components import Dropdown as Dropdown
from webcompy.ui.components import Modal as Modal
from webcompy.ui.components import Spinner as Spinner
from webcompy.ui.components import Tabs as Tabs
from webcompy.ui.components import ToastHost as ToastHost

__all__ = [
    "Accordion",
    "Collapse",
    "Drawer",
    "Dropdown",
    "Modal",
    "Spinner",
    "Tabs",
    "ToastHost",
    "code_block",
    "components",
    "headless",
    "theme",
]
