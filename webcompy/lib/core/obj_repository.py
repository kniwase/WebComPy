from typing import Any, Dict
from .uniq_id import generate_uid_str


repository: Dict[str, Any] = {}


def add_obj(value: Any, prefix: str = '') -> str:
    idx = generate_uid_str(repository, prefix)
    repository[idx] = value
    return idx


def pop_obj(idx: str) -> Any:
    return repository.pop(idx)
