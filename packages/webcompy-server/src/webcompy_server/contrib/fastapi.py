from __future__ import annotations

from json import dumps as json_dumps
from typing import Any, Literal

try:
    from starlette.responses import JSONResponse
except ImportError as err:
    raise ImportError(
        "webcompy_server.contrib.fastapi requires Starlette/FastAPI. Install it with: pip install fastapi"
    ) from err

from webcompy.hydration._transfer_meta import META_HEADER_NAME, encode_with_meta, merge_meta_into_body


class TypedJSONResponse(JSONResponse):
    def __init__(
        self,
        content: Any,
        *,
        transfer_mode: Literal["header", "body"] = "header",
        **kwargs: Any,
    ) -> None:
        json_data, meta = encode_with_meta(content)
        if transfer_mode == "body":
            json_data = merge_meta_into_body(json_data, meta)
        elif meta:
            headers = dict(kwargs.pop("headers", None) or {})
            headers[META_HEADER_NAME] = json_dumps(meta, separators=(",", ":"))
            kwargs["headers"] = headers
        super().__init__(json_data, **kwargs)
