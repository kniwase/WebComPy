from webcompy.ajax._multipart import encode_multipart


class TestEncodeMultipart:
    def test_content_type_media_type_and_boundary(self):
        _, content_type = encode_multipart({"a": "1"})
        assert content_type.startswith("multipart/form-data; boundary=")
        boundary = content_type.rsplit("=", 1)[1]
        assert boundary.isalnum()
        assert len(boundary) == 32

    def test_boundaries_are_unique(self):
        _, first = encode_multipart({"a": "1"})
        _, second = encode_multipart({"a": "1"})
        assert first != second

    def test_text_field_framing(self):
        body, content_type = encode_multipart({"a": "1"})
        boundary = content_type.rsplit("=", 1)[1]
        assert body == (
            f'--{boundary}\r\nContent-Disposition: form-data; name="a"\r\n\r\n1\r\n'.encode()
            + f"--{boundary}--\r\n".encode()
        )

    def test_bytes_field_passes_through_verbatim(self):
        body, _ = encode_multipart({"blob": b"\x00\x01\xff"})
        assert b"\x00\x01\xff" in body

    def test_multiple_fields_preserve_order(self):
        body, content_type = encode_multipart({"a": "1", "b": "2", "c": "3"})
        content_type.rsplit("=", 1)[1]
        positions = [body.index(f'name="{name}"'.encode()) for name in ("a", "b", "c")]
        assert positions == sorted(positions)
        assert b'name="a"\r\n\r\n1\r\n' in body
        assert b'name="b"\r\n\r\n2\r\n' in body
        assert b'name="c"\r\n\r\n3\r\n' in body

    def test_terminator_present(self):
        body, content_type = encode_multipart({})
        boundary = content_type.rsplit("=", 1)[1]
        assert body == f"--{boundary}--\r\n".encode()

    def test_multibyte_text_values_are_utf8_encoded(self):
        body, _ = encode_multipart({"greeting": "こんにちは"})
        assert "こんにちは".encode() in body
