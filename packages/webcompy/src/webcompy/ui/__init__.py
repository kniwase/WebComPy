"""First-party UI toolkit: theme system, code blocks, and UI primitives.

The themed components are re-exported as the default convenient path;
the headless variants stay under :mod:`webcompy.ui.headless` for
full design control.
"""

from webcompy.ui import code_block as code_block
from webcompy.ui import components as components
from webcompy.ui import headless as headless
from webcompy.ui import theme as theme
from webcompy.ui.components import Spinner as Spinner

__all__ = ["Spinner", "code_block", "components", "headless", "theme"]
