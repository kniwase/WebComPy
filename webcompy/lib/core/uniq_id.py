from random import random
from typing import Dict, Any


def generate_uid(repository: Dict[int, Any]):
    while True:
        new_id = abs(hash(random()))
        if new_id not in repository:
            return new_id


def generate_uid_str(repository: Dict[str, Any], prefix: str = ''):
    while True:
        new_key = f'{prefix}{abs(hash(random()))}'
        if new_key not in repository:
            return new_key
