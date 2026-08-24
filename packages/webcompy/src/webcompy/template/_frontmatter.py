"""Extracts and parses frontmatter blocks from Markdown documents."""

from __future__ import annotations

import tomllib
from typing import Any

from webcompy.exception import WebComPyException

_FLAT_DELIMITER = "---"
_TOML_DELIMITER = "+++"


def split_frontmatter(source: str) -> tuple[dict[str, Any], str]:
    lines = source.splitlines(keepends=True)
    if not lines:
        return {}, source
    first = lines[0].rstrip("\r\n")
    if first == _FLAT_DELIMITER:
        delimiter, parse = _FLAT_DELIMITER, _parse_flat
    elif first == _TOML_DELIMITER:
        delimiter, parse = _TOML_DELIMITER, _parse_toml
    else:
        return {}, source
    for i in range(1, len(lines)):
        if lines[i].rstrip("\r\n") == delimiter:
            block = "".join(lines[1:i])
            body = "".join(lines[i + 1 :])
            return parse(block), body
    raise WebComPyException(f"Unterminated frontmatter block: opening '{delimiter}' has no closing '{delimiter}' line")


def _parse_flat(block: str) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    for line in block.splitlines():
        if not line.strip():
            continue
        key, sep, value = line.partition(":")
        if not sep:
            raise WebComPyException(f"Malformed flat frontmatter line (expected 'key: value'): {line!r}")
        metadata[key.strip()] = value.strip()
    return metadata


def _parse_toml(block: str) -> dict[str, Any]:
    try:
        return tomllib.loads(block)
    except tomllib.TOMLDecodeError as exc:
        raise WebComPyException(f"Invalid TOML frontmatter: {exc}") from exc
