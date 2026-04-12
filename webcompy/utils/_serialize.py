from typing import Any


def _is_json_seriarizable_value(obj: Any) -> bool:
    if isinstance(obj, list):
        return all(_is_json_seriarizable_value(c) for c in obj)  # type: ignore
    elif isinstance(obj, dict):
        return all(isinstance(k, str) for k in obj) and all(_is_json_seriarizable_value(v) for v in obj.values())  # type: ignore
    elif isinstance(obj, (str, int, float, bool)) or obj is None:
        return True
    return False


def is_json_seriarizable(obj: Any) -> bool:
    return isinstance(obj, (list, dict)) and _is_json_seriarizable_value(obj)  # type: ignore
