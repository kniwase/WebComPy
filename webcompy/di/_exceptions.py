from __future__ import annotations


class InjectionError(Exception):
    def __init__(self, key: object) -> None:
        from webcompy.di._key import InjectKey

        if isinstance(key, InjectKey):
            description = f"InjectKey({key.name!r})"
        elif isinstance(key, type):
            description = key.__name__
        else:
            description = repr(key)
        super().__init__(f"No provider found for {description}")
