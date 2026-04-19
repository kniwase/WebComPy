from __future__ import annotations


class InjectionError(Exception):
    def __init__(self, key: object, message: str = "") -> None:
        from webcompy.di._key import InjectKey

        if isinstance(key, InjectKey):
            key_desc = repr(key)
        elif isinstance(key, type):
            key_desc = key.__name__
        else:
            key_desc = str(key)

        msg = message or f"No provider found for {key_desc}"

        super().__init__(msg)
        self._key = key
