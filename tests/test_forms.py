from __future__ import annotations

import pytest

from webcompy.exception import WebComPyException
from webcompy.forms import (
    email,
    max_length,
    max_value,
    min_length,
    min_value,
    pattern,
    required,
    use_field,
)
from webcompy.signal import Signal


class TestField:
    def test_creating_a_field(self):
        field = use_field(Signal(""), validators=[required()])
        assert field.valid.value is False
        assert field.errors.value == ["This field is required"]
        assert field.touched.value is False
        assert field.dirty.value is False

    def test_value_is_same_signal_object(self):
        sig = Signal("")
        field = use_field(sig, validators=[required()])
        assert field.value is sig

    def test_errors_react_to_value_changes(self):
        field = use_field(Signal(""), validators=[required()])
        assert field.errors.value == ["This field is required"]
        assert field.valid.value is False
        field.value.value = "alice"
        assert field.errors.value == []
        assert field.valid.value is True
        assert field.invalid.value is False

    def test_reset_restores_initial_state(self):
        field = use_field(Signal("initial"), validators=[required()])
        field.value.value = "changed"
        field.touched.value = True
        field.dirty.value = True
        field.reset()
        assert field.value.value == "initial"
        assert field.touched.value is False
        assert field.dirty.value is False

    def test_invalid_derived_from_errors(self):
        field = use_field(Signal(""), validators=[required()])
        assert field.invalid.value is True
        field.value.value = "x"
        assert field.invalid.value is False

    def test_name_attribute(self):
        field = use_field(Signal(""), name="email")
        assert field.name == "email"

    def test_not_a_signal_base(self):
        from webcompy.signal import SignalBase

        field = use_field(Signal("x"))
        assert not isinstance(field, SignalBase)


class TestValidators:
    def test_required_missing_values(self):
        validate = required()
        assert validate(None) is not None
        assert validate("") is not None
        assert validate("   ") is not None
        assert validate(False) is not None

    def test_required_accepts_values(self):
        validate = required()
        assert validate("x") is None
        assert validate(0) is None
        assert validate(True) is None

    def test_required_with_checkbox_false(self):
        assert required()(False) is not None

    def test_custom_message(self):
        assert min_length(8, message="Too short")("abc") == "Too short"

    def test_min_length(self):
        validate = min_length(8)
        assert validate("abc") is not None
        assert validate("12345678") is None

    def test_max_length(self):
        validate = max_length(4)
        assert validate("abcde") is not None
        assert validate("abcd") is None

    def test_min_length_non_sized_raises(self):
        validate = min_length(8)
        with pytest.raises(WebComPyException, match="sized"):
            validate(5)

    def test_max_length_non_sized_raises(self):
        validate = max_length(8)
        with pytest.raises(WebComPyException, match="sized"):
            validate(5)

    def test_pattern(self):
        validate = pattern(r"^[A-Z]+$")
        assert validate("ABC") is None
        assert validate("abc") is not None

    def test_pattern_non_str_raises(self):
        validate = pattern(r"^[A-Z]+$")
        with pytest.raises(WebComPyException, match="str"):
            validate(5)

    def test_email_valid(self):
        validate = email()
        assert validate("alice@example.com") is None

    def test_email_invalid(self):
        validate = email()
        assert validate("not-an-email") is not None
        assert validate("a@b") is not None

    def test_min_value(self):
        validate = min_value(10)
        assert validate(5) is not None
        assert validate(15) is None

    def test_max_value(self):
        validate = max_value(10)
        assert validate(15) is not None
        assert validate(5) is None

    def test_min_value_non_orderable_raises(self):
        validate = min_value(10)
        with pytest.raises(WebComPyException, match="orderable"):
            validate("abc")

    def test_max_value_non_orderable_raises(self):
        validate = max_value(10)
        with pytest.raises(WebComPyException, match="orderable"):
            validate("abc")

    def test_multiple_validators_accumulate(self):
        field = use_field(Signal(""), validators=[required(), min_length(8)])
        assert "This field is required" in field.errors.value
