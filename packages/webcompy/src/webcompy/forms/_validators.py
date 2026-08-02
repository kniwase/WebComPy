from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any, TypeAlias, TypeVar

from webcompy.exception import WebComPyException

T = TypeVar("T")

Validator: TypeAlias = Callable[[T], str | None]


def required(message: str = "This field is required") -> Validator[Any]:
    def validate(v: Any) -> str | None:
        if v is None or v is False:
            return message
        if isinstance(v, str) and not v.strip():
            return message
        return None

    return validate


def min_length(n: int, message: str | None = None) -> Validator[Any]:
    msg = message if message is not None else f"Must be at least {n} characters"

    def validate(v: Any) -> str | None:
        try:
            length = len(v)
        except TypeError as err:
            raise WebComPyException(f"min_length validator requires a sized value (got {type(v).__name__})") from err
        if length < n:
            return msg
        return None

    return validate


def max_length(n: int, message: str | None = None) -> Validator[Any]:
    msg = message if message is not None else f"Must be at most {n} characters"

    def validate(v: Any) -> str | None:
        try:
            length = len(v)
        except TypeError as err:
            raise WebComPyException(f"max_length validator requires a sized value (got {type(v).__name__})") from err
        if length > n:
            return msg
        return None

    return validate


def pattern(regex: str, message: str = "Invalid format") -> Validator[Any]:
    compiled = re.compile(regex)

    def validate(v: Any) -> str | None:
        if not isinstance(v, str):
            raise WebComPyException(f"pattern validator requires a str value (got {type(v).__name__})")
        if compiled.search(v) is None:
            return message
        return None

    return validate


def email(message: str = "Invalid email address") -> Validator[Any]:
    return pattern(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", message)


def min_value(n: float, message: str | None = None) -> Validator[Any]:
    msg = message if message is not None else f"Must be at least {n}"

    def validate(v: Any) -> str | None:
        try:
            too_small = v < n
        except TypeError as err:
            raise WebComPyException(
                f"min_value validator requires an orderable value (got {type(v).__name__})"
            ) from err
        if too_small:
            return msg
        return None

    return validate


def max_value(n: float, message: str | None = None) -> Validator[Any]:
    msg = message if message is not None else f"Must be at most {n}"

    def validate(v: Any) -> str | None:
        try:
            too_large = v > n
        except TypeError as err:
            raise WebComPyException(
                f"max_value validator requires an orderable value (got {type(v).__name__})"
            ) from err
        if too_large:
            return msg
        return None

    return validate
