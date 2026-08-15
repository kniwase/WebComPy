from __future__ import annotations

from re import compile as re_compile
from typing import Final

_camel_to_kebab_pattern: Final = re_compile("((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))")


def pascal_to_kebab(name: str) -> str:
    """Convert PascalCase to kebab-case.

    >>> pascal_to_kebab("UserCard")
    'user-card'
    >>> pascal_to_kebab("ToDoListPage")
    'to-do-list-page'
    >>> pascal_to_kebab("MyHTTPClient")
    'my-http-client'
    """
    return _camel_to_kebab_pattern.sub(r"-\1", name).lower()


def kebab_to_pascal(kebab: str) -> str:
    """Convert kebab-case to PascalCase.

    >>> kebab_to_pascal("user-card")
    'UserCard'
    >>> kebab_to_pascal("my-widget")
    'MyWidget'
    >>> kebab_to_pascal("a-b-c")
    'ABC'
    """
    return "".join(part.capitalize() for part in kebab.split("-"))


def kebab_to_snake(kebab: str) -> str:
    """Convert kebab-case to snake_case.

    >>> kebab_to_snake("item-count")
    'item_count'
    >>> kebab_to_snake("data-value")
    'data_value'
    """
    return kebab.replace("-", "_")
