from json import loads as json_loads, dumps as json_dumps
from typing import Any, Dict, Literal, Union
import urllib.parse
from webcompy.elements.types._refference import DomNodeRef
from webcompy.exception import WebComPyException
from webcompy._browser._modules import browser


# HttpClient
class WebComPyHttpClientException(WebComPyException):
    pass


class Response:
    _text: str
    _headers: dict[str, str]
    _status_code: int
    _reason: str
    _ok: bool

    def __init__(
        self,
        text: str,
        headers: dict[str, str],
        status_code: int,
        reason: str,
        ok: bool,
    ) -> None:
        self._text = text
        self._headers = headers
        self._status_code = status_code
        self._reason = reason
        self._ok = ok

    def __repr__(self) -> str:
        return (
            "Response("
            + ", ".join(
                n + "=" + (f"'{v}'" if isinstance(v, str) else str(v))
                for n, v in sorted(
                    map(
                        lambda name: (name[1:], getattr(self, name)),
                        filter(
                            lambda name: name.startswith("_"),
                            self.__annotations__.keys(),
                        ),
                    ),
                    key=lambda li: li[0],
                )
            )
            + ")"
        )

    def raise_for_status(self):
        if not self._ok:
            raise WebComPyHttpClientException

    def json(self, **kwargs: Any) -> dict[str, Any]:
        return json_loads(self._text, **kwargs)

    @property
    def text(self):
        return self._text

    @property
    def headers(self):
        return self._headers

    @property
    def status_code(self):
        return self._status_code

    @property
    def ok(self):
        return self._ok


class HttpClient:
    @classmethod
    async def request(
        cls,
        method: Literal["GET", "OPTIONS", "HEAD", "POST", "PUT", "PATCH", "DELETE"],
        url: str,
        headers: Union[Dict[str, str], None] = None,
        query_params: Union[Dict[str, str], None] = None,
        json: Union[Dict[str, Any], None] = None,
        body_data: Union[str, bytes, None] = None,
        form_data: Union[Dict[str, Union[str, bytes]], None] = None,
        form_element: Union[DomNodeRef, None] = None,
    ) -> Response:
        if browser:
            # query
            if query_params is not None:
                send_url = url + "?" + urllib.parse.urlencode(query_params)
            else:
                send_url = url
            # header
            req_headers = dict(
                tuple(map(urllib.parse.quote, map(str, it)))
                for it in (headers if headers else {}).items()
            )
            # body
            has_body = any(
                (
                    json is not None,
                    body_data is not None,
                    form_data is not None,
                    form_element is not None,
                )
            )
            if has_body:
                if json is not None:
                    req_headers["Content-Type"] = "application/json"
                    body = json_dumps(json, ensure_ascii=True)
                elif body_data is not None:
                    body = body_data
                elif form_data is not None:
                    body = browser.window.FormData.new()
                    for key, value in form_data.items():
                        body.set(key, value)
                elif form_element is not None:
                    body = browser.window.FormData.new(form_element.node)
                else:
                    body = browser.javascript.UNDEFINED
                options = {"method": method, "headers": req_headers, "body": body}
            else:
                options = {"method": method, "headers": req_headers}
            try:
                res = await browser.window.fetch(send_url, options)
            except Exception as err:
                raise WebComPyHttpClientException(str(err))
            else:
                return Response(
                    text=(await res.text()),
                    headers=dict(zip(res.headers.keys(), res.headers.values())),
                    status_code=res.status,
                    reason=res.statusText,
                    ok=res.ok,
                )
        else:
            raise WebComPyHttpClientException

    @classmethod
    async def get(
        cls,
        url: str,
        query_params: Union[Dict[str, str], None] = None,
        headers: Union[Dict[str, str], None] = None,
    ) -> Response:
        if browser:
            res = await HttpClient.request(
                "GET", url, headers=headers, query_params=query_params
            )
            return res
        else:
            raise WebComPyHttpClientException

    @classmethod
    async def head(
        cls,
        url: str,
        query_params: Union[Dict[str, str], None] = None,
        headers: Union[Dict[str, str], None] = None,
    ) -> Response:
        if browser:
            res = await HttpClient.request(
                "HEAD", url, headers=headers, query_params=query_params
            )
            return res
        else:
            raise WebComPyHttpClientException

    @classmethod
    async def options(
        cls,
        url: str,
        query_params: Union[Dict[str, str], None] = None,
        headers: Union[Dict[str, str], None] = None,
    ) -> Response:
        if browser:
            res = await HttpClient.request(
                "OPTIONS", url, headers=headers, query_params=query_params
            )
            return res
        else:
            raise WebComPyHttpClientException

    @classmethod
    async def post(
        cls,
        url: str,
        headers: Union[Dict[str, str], None] = None,
        query_params: Union[Dict[str, str], None] = None,
        json: Union[Dict[str, Any], None] = None,
        body_data: Union[str, bytes, None] = None,
        form_data: Union[Dict[str, Union[str, bytes]], None] = None,
        form_element: Union[DomNodeRef, None] = None,
    ) -> Response:
        if browser:
            res = await HttpClient.request(
                "POST",
                url,
                headers=headers,
                query_params=query_params,
                json=json,
                body_data=body_data,
                form_data=form_data,
                form_element=form_element,
            )
            return res
        else:
            raise WebComPyHttpClientException

    @classmethod
    async def put(
        cls,
        url: str,
        headers: Union[Dict[str, str], None] = None,
        query_params: Union[Dict[str, str], None] = None,
        json: Union[Dict[str, Any], None] = None,
        body_data: Union[str, bytes, None] = None,
        form_data: Union[Dict[str, Union[str, bytes]], None] = None,
        form_element: Union[DomNodeRef, None] = None,
    ) -> Response:
        if browser:
            res = await HttpClient.request(
                "PUT",
                url,
                headers=headers,
                query_params=query_params,
                json=json,
                body_data=body_data,
                form_data=form_data,
                form_element=form_element,
            )
            return res
        else:
            raise WebComPyHttpClientException

    @classmethod
    async def delete(
        cls,
        url: str,
        headers: Union[Dict[str, str], None] = None,
        query_params: Union[Dict[str, str], None] = None,
        json: Union[Dict[str, Any], None] = None,
        body_data: Union[str, bytes, None] = None,
        form_data: Union[Dict[str, Union[str, bytes]], None] = None,
        form_element: Union[DomNodeRef, None] = None,
    ) -> Response:
        if browser:
            res = await HttpClient.request(
                "DELETE",
                url,
                headers=headers,
                query_params=query_params,
                json=json,
                body_data=body_data,
                form_data=form_data,
                form_element=form_element,
            )
            return res
        else:
            raise WebComPyHttpClientException

    @classmethod
    async def patch(
        cls,
        url: str,
        headers: Union[Dict[str, str], None] = None,
        query_params: Union[Dict[str, str], None] = None,
        json: Union[Dict[str, Any], None] = None,
        body_data: Union[str, bytes, None] = None,
        form_data: Union[Dict[str, Union[str, bytes]], None] = None,
        form_element: Union[DomNodeRef, None] = None,
    ) -> Response:
        if browser:
            res = await HttpClient.request(
                "PATCH",
                url,
                headers=headers,
                query_params=query_params,
                json=json,
                body_data=body_data,
                form_data=form_data,
                form_element=form_element,
            )
            return res
        else:
            raise WebComPyHttpClientException
