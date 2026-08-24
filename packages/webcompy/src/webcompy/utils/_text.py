"""Text helpers for dedented multiline strings."""

from functools import partial
from itertools import dropwhile
from re import compile as re_compile

_is_blank_line = re_compile(r"^\s*$").match
_get_head_blanks = re_compile(r"^\s+").match


def strip_multiline_text(text: str):
    """Strip leading blank lines and dedent the remaining block.

    Args:
        text: Multiline string whose first line determines the common
            leading whitespace to remove.

    Returns:
        The dedented text with leading blank lines removed.

    """
    lines = list(dropwhile(_is_blank_line, text.split("\n")))
    if lines:
        if head_blanks := _get_head_blanks(lines[0]):
            return "\n".join(
                map(
                    partial(re_compile("^" + head_blanks.group()).sub, ""),
                    lines,
                )
            )
        else:
            return "\n".join(lines)
    else:
        return ""
