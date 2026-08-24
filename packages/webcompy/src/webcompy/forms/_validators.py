"""Built-in validator factories for form fields."""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any, TypeAlias, TypeVar

from webcompy.exception import WebComPyException

T = TypeVar("T")

Validator: TypeAlias = Callable[[T], str | None]
"""Callable that validates a value and returns an error message, or ``None`` when the value is valid."""


def required(message: str = "This field is required") -> Validator[Any]:
    """Build a validator rejecting ``None``, ``False``, and blank strings.

    Falsy but listed values such as ``0`` or ``[]`` pass validation;
    only ``None``, ``False``, and strings that are empty or whitespace
    fail.

    Args:
        message: Error message returned for failing values.

    Returns:
        A ``Validator`` applying the rejection rule.

    """

    def validate(v: Any) -> str | None:
        if v is None or v is False:
            return message
        if isinstance(v, str) and not v.strip():
            return message
        return None

    return validate


def min_length(n: int, message: str | None = None) -> Validator[Any]:
    """Build a validator requiring values of length at least ``n``.

    Args:
        n: Minimum acceptable length.
        message: Error message returned for shorter values. Defaults to a
            message derived from ``n``.

    Returns:
        A ``Validator`` returning the message when ``len(value) < n``.

    """
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
    """Build a validator requiring values of length at most ``n``.

    Args:
        n: Maximum acceptable length.
        message: Error message returned for longer values. Defaults to a
            message derived from ``n``.

    Returns:
        A ``Validator`` returning the message when ``len(value) > n``.

    """
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
    """Build a validator requiring string values to match a regex.

    Args:
        regex: Regular expression searched against the value.
        message: Error message returned when the value does not match.

    Returns:
        A ``Validator`` returning the message when ``regex`` does not
        match the value.

    """
    compiled = re.compile(regex)

    def validate(v: Any) -> str | None:
        if not isinstance(v, str):
            raise WebComPyException(f"pattern validator requires a str value (got {type(v).__name__})")
        if compiled.search(v) is None:
            return message
        return None

    return validate


def email(message: str = "Invalid email address") -> Validator[Any]:
    """Build a validator for email addresses.

    Uses a simple pattern that requires a ``user@domain.tld`` shape.

    Args:
        message: Error message returned for non-matching values.

    Returns:
        A ``Validator`` rejecting values that do not look like email
        addresses.

    """
    return pattern(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", message)


def min_value(n: float, message: str | None = None) -> Validator[Any]:
    """Build a validator requiring values of at least ``n``.

    Args:
        n: Minimum acceptable value.
        message: Error message returned for smaller values. Defaults to a
            message derived from ``n``.

    Returns:
        A ``Validator`` returning the message when ``value < n``.

    """
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
    """Build a validator requiring values of at most ``n``.

    Args:
        n: Maximum acceptable value.
        message: Error message returned for larger values. Defaults to a
            message derived from ``n``.

    Returns:
        A ``Validator`` returning the message when ``value > n``.

    """
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
