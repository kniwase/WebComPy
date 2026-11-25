---
title: Forms
description: Complete form built with use_field, use_form, validators, and accessible first-party WebComPy UI form controls (Input, Select, Textarea, Checkbox, Switch, RadioGroup, FormField).
---

# Forms

This example showcases a validated signup form combining `webcompy.forms` state management (`use_field`, `use_form`, built-in and custom validators) with accessible themed controls from `webcompy.ui`.

Use this pattern for multi-field workflows requiring blur-gated error display, ARIA descriptions, collective validation on submit, and clean reset behavior.

## What this demonstrates

- **Reactive fields and validators**: Each `use_field(use_state(...), validators=[...])` tracks `value`, `touched`, `dirty`, and `errors` automatically while built-in `required()`, `min_length()`, `email()`, and custom lambdas validate live as the user edits.
- **Accessible `FormField` wiring**: `FormField` injects DI-scoped association IDs into its slotted control (`Input`, `Select`, `Textarea`, `Checkbox`, `RadioGroup`), toggling `aria-invalid`, `aria-describedby`, and `data-state="invalid"` only after a field is touched or the form submits.
- **Independent switches alongside validated fields**: `Switch` binds standalone preference booleans (`updates_field`, `marketing_field`) via `:bind` even when they do not carry validation rules.
- **Submit & reset orchestration**: `form.submit(handler)` prevents default form submission, touches all registered fields, aborts on validation errors, or passes a typed snapshot dictionary to `_on_submit(values)`; `form.reset()` clears touched/dirty flags and restores defaults.

## Key mechanisms and how to adapt

1. **Async submissions**: Change `_on_submit` to `async def _on_submit(values)` and bind `"disabled": form.submitting` on the submit button to prevent double submits while awaiting `HttpClient.post(...)`.
2. **Custom styling with headless controls**: Import controls from `webcompy.ui.headless` instead of `webcompy.ui` when applying a custom design system while retaining keyboard, `data-state`, and ARIA semantics.
3. **Custom cross-field rules**: Check relationships across `form.values()` inside `_on_submit` or compute derived warnings with `use_computed(...)`.

## Next steps

- Learn validator APIs and `:bind` rules in [Forms](/documents/basic/forms).
- Inspect headless vs. themed contracts and DI slot association IDs in [UI Headless Contract](/documents/advanced/ui-headless-contract) and [UI Primitives](/documents/basic/ui-primitives).
- Wire form submission through a mocked or real HTTP endpoint in [Fetch Middleware](/documents/examples/fetch-middleware).
