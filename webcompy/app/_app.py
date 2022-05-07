from typing import Dict, List, Optional, Tuple, TypedDict
from webcompy.components import ComponentGenerator
from webcompy.router import Router
from webcompy.app._root_component import AppDocumentRoot


class Head(TypedDict, total=False):
    title: str
    meta: List[Dict[str, str]]
    link: List[Dict[str, str]]
    script: List[Tuple[Dict[str, str], Optional[str]]]


class WebComPyApp:
    _root: AppDocumentRoot
    _head: Head
    _scripts: List[Tuple[Dict[str, str], Optional[str]]]

    def __init__(
        self,
        *,
        root_component: ComponentGenerator[None],
        router: Router | None = None,
    ) -> None:
        self._head: Head = {"meta": [], "link": [], "script": []}
        self._scripts = []
        self._root = AppDocumentRoot(root_component, router)

    def set_title(self, title: str):
        self._head["title"] = title

    def append_meta(self, attributes: Dict[str, str]):
        if "meta" in self._head:
            self._head["meta"].append(attributes)
        else:
            self._head["meta"] = [attributes]

    def append_link(self, attributes: Dict[str, str]):
        if "link" in self._head:
            self._head["link"].append(attributes)
        else:
            self._head["link"] = [attributes]

    def append_script(
        self,
        attributes: Dict[str, str],
        script: str | None = None,
        in_head: bool = False,
    ):
        if not in_head:
            self._scripts.append((attributes, script))
        elif "script" in self._head:
            self._head["script"].append((attributes, script))
        else:
            self._head["script"] = [(attributes, script)]

    def set_head(self, head: Head):
        self._head = head

    def update_head(self, head: Head):
        if "title" in head:
            self.set_title(head["title"])
        for meta in head.get("meta", []):
            self.append_meta(meta)
        for link in head.get("link", []):
            self.append_link(link)
        for attrs, script in head.get("script", []):
            self.append_script(attrs, script, True)

    @property
    def __component__(self):
        return self._root

    @property
    def __head__(self):
        return self._head

    @property
    def __scripts__(self):
        return self._scripts
