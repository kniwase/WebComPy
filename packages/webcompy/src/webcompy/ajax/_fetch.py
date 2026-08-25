"""Typed HTTP client whose requests are routed through the injected ``FetchPort``."""

import urllib.parse  # noqa: I001
from collections.abc import Mapping
from json import JSONDecodeError
from json import dumps as json_dumps
from json import loads as json_loads
from typing import Any, Literal, TypeVar, overload

from webcompy.ajax._multipart import encode_multipart
from webcompy.ajax._serde import TypedResponseError, from_json
from webcompy.elements.types._refference import DomNodeRef
from webcompy.exception import WebComPyException
from webcompy.di import inject
from webcompy.hydration._transfer_meta import META_BODY_KEY, META_HEADER_NAME
from webcompy.ports._keys import FETCH_PORT_KEY, FFI_PORT_KEY

T = TypeVar("T")

_META_HEADER_NAME_LOWER = META_HEADER_NAME.lower()


# HttpClient
class WebComPyHttpClientException(WebComPyException):
    """Raised when an HTTP request fails or a response status is not OK."""

    pass


class Response:
    """An HTTP response returned by :class:`HttpClient`.

    Args:
        text: Response body as decoded text.
        headers: Response headers as a ``{name: value}`` mapping.
        status_code: HTTP status code.
        reason: Human-readable HTTP status text.
        ok: Whether the status code is in the success range.

    Attributes:
        text: Response body as decoded text.
        headers: Response headers as a ``{name: value}`` mapping.
        status_code: HTTP status code.
        ok: Whether the status code is in the success range.

    """

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
        """Raise an error when the response has a non-success status.

        Raises:
            WebComPyHttpClientException: When ``ok`` is ``False``.

        """
        if not self._ok:
            raise WebComPyHttpClientException

    def json(self, **kwargs: Any) -> dict[str, Any]:
        """Parse the response body as a JSON object.

        Args:
            **kwargs: Keyword arguments forwarded to ``json.loads``.

        Returns:
            The parsed JSON value.

        """
        return json_loads(self._text, **kwargs)

    @property
    def text(self):
        """The response body text.

        Returns:
            The response body as decoded text.

        """
        return self._text

    @property
    def headers(self):
        """The response headers.

        Returns:
            A ``{name: value}`` mapping of the response headers.

        """
        return self._headers

    @property
    def status_code(self):
        """The HTTP status code.

        Returns:
            The integer HTTP status code.

        """
        return self._status_code

    @property
    def ok(self):
        """Whether the status code is in the success range.

        Returns:
            ``True`` when the HTTP status code is in the success range.

        """
        return self._ok


def _deserialize_if_typed(res: Response, response_type: type[T] | None) -> Response | T:
    if response_type is None:
        return res
    res.raise_for_status()
    try:
        data = json_loads(res.text)
    except (JSONDecodeError, TypeError) as err:
        raise TypedResponseError(f"Failed to parse response as JSON: {res.text[:200]!r}") from err
    meta = None
    if isinstance(data, dict) and META_BODY_KEY in data:
        meta = data.pop(META_BODY_KEY)
        if not isinstance(meta, Mapping):
            raise TypedResponseError(f"Malformed {META_BODY_KEY}: expected a JSON object, got {type(meta).__name__}")
    else:
        header_value = next((v for k, v in res.headers.items() if k.lower() == _META_HEADER_NAME_LOWER), None)
        if header_value is not None:
            try:
                meta = json_loads(header_value)
            except (JSONDecodeError, TypeError) as err:
                raise TypedResponseError(f"Malformed {META_HEADER_NAME} header") from err
    try:
        return from_json(response_type, data, meta=meta)
    except (TypeError, ValueError) as err:
        raise TypedResponseError(f"Response does not match schema: {err}; body excerpt: {res.text[:200]!r}") from err


def _port_response_to_client(ports_res: Any) -> Response:
    return Response(
        text=ports_res.text,
        headers=ports_res.headers,
        status_code=ports_res.status_code,
        reason=ports_res.status_text,
        ok=ports_res.ok,
    )


class HttpClient:
    """Static HTTP client whose requests are routed through the ``FetchPort``.

    All operations are classmethods returning a :class:`Response`, or a typed
    value when ``response_type`` is given.
    """

    @classmethod
    async def request(
        cls,
        method: Literal["GET", "OPTIONS", "HEAD", "POST", "PUT", "PATCH", "DELETE"],
        url: str,
        headers: dict[str, str] | None = None,
        query_params: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        body_data: str | bytes | None = None,
        form_data: dict[str, str | bytes] | None = None,
        form_element: DomNodeRef | None = None,
    ) -> Response:
        """Send a raw HTTP request and return the response.

        Args:
            method: HTTP method to use.
            url: Request URL.
            headers: Request headers as a ``{name: value}`` mapping.
            query_params: Query parameters appended to the URL.
            json: JSON object serialized as the request body.
            body_data: Raw ``str`` or ``bytes`` request body.
            form_data: Multipart form fields encoded and sent through the fetch port.
            form_element: A form DOM node whose fields are submitted (browser only).

        Returns:
            The parsed :class:`Response`.

        Raises:
            WebComPyHttpClientException: If the request cannot be dispatched.

        """
        # query
        send_url = url + "?" + urllib.parse.urlencode(query_params) if query_params is not None else url
        # header
        raw_headers = dict(headers) if headers else {}
        req_headers = {urllib.parse.quote(str(k)): urllib.parse.quote(str(v)) for k, v in raw_headers.items()}
        has_content_type = any(name.lower() == "content-type" for name in raw_headers)
        # body
        has_body = any(
            (
                json is not None,
                body_data is not None,
                form_data is not None,
                form_element is not None,
            )
        )
        if form_data is not None:
            body, media_type = encode_multipart(form_data)
            if not has_content_type:
                req_headers["Content-Type"] = media_type
            try:
                ports_res = await inject(FETCH_PORT_KEY).fetch(send_url, method=method, headers=req_headers, body=body)
            except Exception as err:
                raise WebComPyHttpClientException(str(err)) from err
            else:
                ret = _port_response_to_client(ports_res)
        elif form_element is not None:
            from webcompy.ports._browser._raw import browser as _raw_browser

            if _raw_browser is None:
                raise WebComPyHttpClientException("form_element requires a browser environment")
            ffi_port = inject(FFI_PORT_KEY)
            req_headers_proxy = ffi_port.create_proxy(req_headers)
            try:
                form_body = _raw_browser.FormData.new(form_element.node)
                res = await _raw_browser.fetch(send_url, method=method, headers=req_headers_proxy, body=form_body)
            except Exception as err:
                raise WebComPyHttpClientException(str(err)) from err
            else:
                headers_obj = res.headers
                ret = Response(
                    text=(await res.text()),
                    headers=dict(
                        zip(
                            list(headers_obj.keys()),
                            list(headers_obj.values()),
                            strict=True,
                        )
                    ),
                    status_code=res.status,
                    reason=res.statusText,
                    ok=res.ok,
                )
            finally:
                ffi_port.destroy_proxy(req_headers_proxy)
        else:
            if method not in {"GET", "OPTIONS", "HEAD"} and has_body:
                if json is not None:
                    req_headers["Content-Type"] = "application/json"
                    body = json_dumps(json, ensure_ascii=True)
                elif body_data is not None:
                    body = body_data if isinstance(body_data, str) else body_data.decode()
                else:
                    body = None
            else:
                body = None

            try:
                ports_res = await inject(FETCH_PORT_KEY).fetch(send_url, method=method, headers=req_headers, body=body)
            except Exception as err:
                raise WebComPyHttpClientException(str(err)) from err
            else:
                ret = _port_response_to_client(ports_res)
        return ret

    @overload
    @classmethod
    async def get(
        cls,
        url: str,
        query_params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
        *,
        response_type: None = None,
    ) -> Response: ...

    @overload
    @classmethod
    async def get(
        cls,
        url: str,
        query_params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
        *,
        response_type: type[T],
    ) -> T: ...

    @classmethod
    async def get(
        cls,
        url: str,
        query_params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
        *,
        response_type: type[T] | None = None,
    ) -> Response | T:
        """Send a GET request.

        Args:
            url: Request URL.
            query_params: Query parameters appended to the URL.
            headers: Request headers as a ``{name: value}`` mapping.
            response_type: When given, deserialize the JSON response body as
                this type instead of returning a :class:`Response`.

        Returns:
            The :class:`Response`, or the typed value when ``response_type`` is given.

        """
        res = await HttpClient.request(
            "GET",
            url,
            headers=headers,
            query_params=query_params,
        )
        return _deserialize_if_typed(res, response_type)

    @overload
    @classmethod
    async def head(
        cls,
        url: str,
        query_params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
        *,
        response_type: None = None,
    ) -> Response: ...

    @overload
    @classmethod
    async def head(
        cls,
        url: str,
        query_params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
        *,
        response_type: type[T],
    ) -> T: ...

    @classmethod
    async def head(
        cls,
        url: str,
        query_params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
        *,
        response_type: type[T] | None = None,
    ) -> Response | T:
        """Send a HEAD request.

        Args:
            url: Request URL.
            query_params: Query parameters appended to the URL.
            headers: Request headers as a ``{name: value}`` mapping.
            response_type: When given, deserialize the JSON response body as
                this type instead of returning a :class:`Response`.

        Returns:
            The :class:`Response`, or the typed value when ``response_type`` is given.

        """
        res = await HttpClient.request(
            "HEAD",
            url,
            headers=headers,
            query_params=query_params,
        )
        return _deserialize_if_typed(res, response_type)

    @overload
    @classmethod
    async def options(
        cls,
        url: str,
        query_params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
        *,
        response_type: None = None,
    ) -> Response: ...

    @overload
    @classmethod
    async def options(
        cls,
        url: str,
        query_params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
        *,
        response_type: type[T],
    ) -> T: ...

    @classmethod
    async def options(
        cls,
        url: str,
        query_params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
        *,
        response_type: type[T] | None = None,
    ) -> Response | T:
        """Send an OPTIONS request.

        Args:
            url: Request URL.
            query_params: Query parameters appended to the URL.
            headers: Request headers as a ``{name: value}`` mapping.
            response_type: When given, deserialize the JSON response body as
                this type instead of returning a :class:`Response`.

        Returns:
            The :class:`Response`, or the typed value when ``response_type`` is given.

        """
        res = await HttpClient.request(
            "OPTIONS",
            url,
            headers=headers,
            query_params=query_params,
        )
        return _deserialize_if_typed(res, response_type)

    @overload
    @classmethod
    async def post(
        cls,
        url: str,
        headers: dict[str, str] | None = None,
        query_params: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        body_data: str | bytes | None = None,
        form_data: dict[str, str | bytes] | None = None,
        form_element: DomNodeRef | None = None,
        *,
        response_type: None = None,
    ) -> Response: ...

    @overload
    @classmethod
    async def post(
        cls,
        url: str,
        headers: dict[str, str] | None = None,
        query_params: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        body_data: str | bytes | None = None,
        form_data: dict[str, str | bytes] | None = None,
        form_element: DomNodeRef | None = None,
        *,
        response_type: type[T],
    ) -> T: ...

    @classmethod
    async def post(
        cls,
        url: str,
        headers: dict[str, str] | None = None,
        query_params: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        body_data: str | bytes | None = None,
        form_data: dict[str, str | bytes] | None = None,
        form_element: DomNodeRef | None = None,
        *,
        response_type: type[T] | None = None,
    ) -> Response | T:
        """Send a POST request.

        Args:
            url: Request URL.
            headers: Request headers as a ``{name: value}`` mapping.
            query_params: Query parameters appended to the URL.
            json: JSON object serialized as the request body.
            body_data: Raw ``str`` or ``bytes`` request body.
            form_data: Multipart form fields encoded and sent through the fetch port.
            form_element: A form DOM node whose fields are submitted (browser only).
            response_type: When given, deserialize the JSON response body as
                this type instead of returning a :class:`Response`.

        Returns:
            The :class:`Response`, or the typed value when ``response_type`` is given.

        """
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
        return _deserialize_if_typed(res, response_type)

    @overload
    @classmethod
    async def put(
        cls,
        url: str,
        headers: dict[str, str] | None = None,
        query_params: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        body_data: str | bytes | None = None,
        form_data: dict[str, str | bytes] | None = None,
        form_element: DomNodeRef | None = None,
        *,
        response_type: None = None,
    ) -> Response: ...

    @overload
    @classmethod
    async def put(
        cls,
        url: str,
        headers: dict[str, str] | None = None,
        query_params: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        body_data: str | bytes | None = None,
        form_data: dict[str, str | bytes] | None = None,
        form_element: DomNodeRef | None = None,
        *,
        response_type: type[T],
    ) -> T: ...

    @classmethod
    async def put(
        cls,
        url: str,
        headers: dict[str, str] | None = None,
        query_params: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        body_data: str | bytes | None = None,
        form_data: dict[str, str | bytes] | None = None,
        form_element: DomNodeRef | None = None,
        *,
        response_type: type[T] | None = None,
    ) -> Response | T:
        """Send a PUT request.

        Args:
            url: Request URL.
            headers: Request headers as a ``{name: value}`` mapping.
            query_params: Query parameters appended to the URL.
            json: JSON object serialized as the request body.
            body_data: Raw ``str`` or ``bytes`` request body.
            form_data: Multipart form fields encoded and sent through the fetch port.
            form_element: A form DOM node whose fields are submitted (browser only).
            response_type: When given, deserialize the JSON response body as
                this type instead of returning a :class:`Response`.

        Returns:
            The :class:`Response`, or the typed value when ``response_type`` is given.

        """
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
        return _deserialize_if_typed(res, response_type)

    @overload
    @classmethod
    async def delete(
        cls,
        url: str,
        headers: dict[str, str] | None = None,
        query_params: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        body_data: str | bytes | None = None,
        form_data: dict[str, str | bytes] | None = None,
        form_element: DomNodeRef | None = None,
        *,
        response_type: None = None,
    ) -> Response: ...

    @overload
    @classmethod
    async def delete(
        cls,
        url: str,
        headers: dict[str, str] | None = None,
        query_params: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        body_data: str | bytes | None = None,
        form_data: dict[str, str | bytes] | None = None,
        form_element: DomNodeRef | None = None,
        *,
        response_type: type[T],
    ) -> T: ...

    @classmethod
    async def delete(
        cls,
        url: str,
        headers: dict[str, str] | None = None,
        query_params: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        body_data: str | bytes | None = None,
        form_data: dict[str, str | bytes] | None = None,
        form_element: DomNodeRef | None = None,
        *,
        response_type: type[T] | None = None,
    ) -> Response | T:
        """Send a DELETE request.

        Args:
            url: Request URL.
            headers: Request headers as a ``{name: value}`` mapping.
            query_params: Query parameters appended to the URL.
            json: JSON object serialized as the request body.
            body_data: Raw ``str`` or ``bytes`` request body.
            form_data: Multipart form fields encoded and sent through the fetch port.
            form_element: A form DOM node whose fields are submitted (browser only).
            response_type: When given, deserialize the JSON response body as
                this type instead of returning a :class:`Response`.

        Returns:
            The :class:`Response`, or the typed value when ``response_type`` is given.

        """
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
        return _deserialize_if_typed(res, response_type)

    @overload
    @classmethod
    async def patch(
        cls,
        url: str,
        headers: dict[str, str] | None = None,
        query_params: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        body_data: str | bytes | None = None,
        form_data: dict[str, str | bytes] | None = None,
        form_element: DomNodeRef | None = None,
        *,
        response_type: None = None,
    ) -> Response: ...

    @overload
    @classmethod
    async def patch(
        cls,
        url: str,
        headers: dict[str, str] | None = None,
        query_params: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        body_data: str | bytes | None = None,
        form_data: dict[str, str | bytes] | None = None,
        form_element: DomNodeRef | None = None,
        *,
        response_type: type[T],
    ) -> T: ...

    @classmethod
    async def patch(
        cls,
        url: str,
        headers: dict[str, str] | None = None,
        query_params: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        body_data: str | bytes | None = None,
        form_data: dict[str, str | bytes] | None = None,
        form_element: DomNodeRef | None = None,
        *,
        response_type: type[T] | None = None,
    ) -> Response | T:
        """Send a PATCH request.

        Args:
            url: Request URL.
            headers: Request headers as a ``{name: value}`` mapping.
            query_params: Query parameters appended to the URL.
            json: JSON object serialized as the request body.
            body_data: Raw ``str`` or ``bytes`` request body.
            form_data: Multipart form fields encoded and sent through the fetch port.
            form_element: A form DOM node whose fields are submitted (browser only).
            response_type: When given, deserialize the JSON response body as
                this type instead of returning a :class:`Response`.

        Returns:
            The :class:`Response`, or the typed value when ``response_type`` is given.

        """
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
        return _deserialize_if_typed(res, response_type)
