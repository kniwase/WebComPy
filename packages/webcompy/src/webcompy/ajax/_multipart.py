"""Multipart/form-data encoding for typed HTTP client form submissions."""

import secrets

_BOUNDARY_LENGTH = 16


def encode_multipart(fields: dict[str, str | bytes]) -> tuple[bytes, str]:
    """Encode simple form fields as a ``multipart/form-data`` body.

    Args:
        fields: Form field names mapped to text or binary values.

    Returns:
        A tuple of the encoded body bytes and the ``Content-Type`` header
        value carrying the generated boundary.

    Raises:
        ValueError: If a field name contains ``"``, ``\\r``, or ``\\n``.

    """
    boundary = secrets.token_hex(_BOUNDARY_LENGTH)
    parts: list[bytes] = []
    for name, value in fields.items():
        if '"' in name or "\r" in name or "\n" in name:
            raise ValueError("form field name must not contain '\"', CR or LF")
        payload = value.encode("utf-8") if isinstance(value, str) else value
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n'.encode() + payload + b"\r\n"
        )
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"
