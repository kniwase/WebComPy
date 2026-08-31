"""Component-scoped context shared between ``FormField`` and its bound controls."""

from __future__ import annotations

from dataclasses import dataclass

from webcompy.di import InjectKey


@dataclass(frozen=True)
class FormFieldContext:
    """Association ids provided by a ``FormField`` to its slotted control.

    The control consumes the context to set its native element's ``id``
    (``control_id``) and, while the field is touched and invalid, to
    reference the FormField's error region (``error_id``) through
    ``aria-describedby``. Both ids are derived from the FormField's
    hydration-stable transfer id, so they match between server-rendered
    markup and the hydrated client tree.

    Args:
        control_id: DOM id the slotted control assigns to its native
            element so the FormField's ``<label for>`` resolves to it.
        error_id: DOM id of the FormField's error message region,
            referenced by the control's ``aria-describedby`` when the
            field is touched and invalid.
        label: Visible label text configured on the FormField, exposed
            for controls that render their own caption (e.g. a
            ``RadioGroup`` legend).

    """

    control_id: str
    error_id: str
    label: str


FORM_FIELD_CONTEXT_KEY: InjectKey[FormFieldContext] = InjectKey("webcompy.ui.form-field-context")
