from typing import Any, Literal
from webcompy.reactive._base import ReactiveBase
from webcompy._browser._modules import browser


class Location(ReactiveBase[str]):
    __mode__: Literal["hash", "history"]
    _value: str
    _state: dict[str, Any] | None
    _base_url: str

    def __init__(self, mode: Literal["hash", "history"], base_url: str) -> None:
        super().__init__("")
        self._state = None
        self._base_url = base_url.strip().strip("/")
        self.set_mode(mode)
        if browser:
            if self.__mode__ == "hash" and self._value == "":
                browser.window.location.replace(
                    f"/{self._base_url}/#/" if self._base_url else "/#/"
                )
            browser.window.addEventListener("popstate", self._refresh_path, False)

    @ReactiveBase._change_event
    def set_mode(self, mode: Literal["hash", "history"]):
        self.__mode__ = mode
        self._refresh_path()

    @property
    @ReactiveBase._get_evnet
    def value(self):
        return self._value

    @property
    @ReactiveBase._get_evnet
    def state(self):
        return self._state

    @ReactiveBase._change_event
    def __set_path__(self, path: str, state: dict[str, Any] | None):
        self._state = state
        if self.__mode__ == "hash" and path.startswith("#"):
            self._value = path[1:]
        else:
            self._value = path

    def _refresh_path(self, _: Any = None):
        if browser and self.__mode__ == "history":
            path: str = (
                browser.window.location.pathname + browser.window.location.search
            )
        elif browser and self.__mode__ == "hash":
            path: str = browser.window.location.hash
        else:
            path: str = ""
        if browser:
            if browser.window.history.state is browser.javascript.NULL:
                self._state = None
            else:
                self._state = browser.window.history.state.to_dict()
        else:
            self._state = None
        self.__set_path__(path, self._state)
