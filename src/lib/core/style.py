from typing import Dict


class Style:
    _selector: str
    _properties: Dict[str, str]

    def __init__(self, selector: str, properties: Dict[str, str]) -> None:
        self._selector = selector
        self._properties = properties

    def __str__(self) -> str:
        properties = '; '.join(
            f'{p}: {v}' for p, v in self._properties.items())
        return f'{self._selector} {{ {properties} }}'


class ImportCss:
    _url: str

    def __init__(self, url: str) -> None:
        self._url = url

    def __str__(self) -> str:
        return f'@import url("{self._url}");'
