from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.forms import email, min_length, required, use_field, use_form
from webcompy.signal import use_computed, use_state


@define_component("form-fields-page")
def FormFieldsPage(context: ComponentContext[None]):
    context.set_title("Form Fields - E2E")

    email_field = use_field(
        use_state(lambda: ""),
        validators=[required(), email()],
        name="email",
    )
    password_field = use_field(
        use_state(lambda: ""),
        validators=[required(), min_length(8)],
        name="password",
    )
    form = use_form(email=email_field, password=password_field)

    logged_in = use_state(lambda: False)

    def on_login(values):
        logged_in.value = True

    return html.DIV(
        {"data-testid": "form-fields-page"},
        html.H2({}, "Form Fields Tests"),
        html.FORM(
            {"@submit": form.submit(on_login)},
            html.DIV(
                {},
                html.INPUT({"data-testid": "ff-email", ":bind": email_field}),
                html.SPAN(
                    {"data-testid": "ff-email-error"},
                    use_computed(
                        lambda: (
                            ", ".join(email_field.errors.value)
                            if email_field.touched.value and email_field.invalid.value
                            else ""
                        )
                    ),
                ),
            ),
            html.DIV(
                {},
                html.INPUT({"data-testid": "ff-password", "type": "password", ":bind": password_field}),
                html.SPAN(
                    {"data-testid": "ff-password-error"},
                    use_computed(
                        lambda: (
                            ", ".join(password_field.errors.value)
                            if password_field.touched.value and password_field.invalid.value
                            else ""
                        )
                    ),
                ),
            ),
            html.BUTTON({"data-testid": "ff-submit", "type": "submit"}, "Login"),
        ),
        html.SPAN({"data-testid": "ff-form-dirty"}, use_computed(lambda: "dirty" if form.dirty.value else "clean")),
        html.SPAN({"data-testid": "ff-status"}, use_computed(lambda: "logged-in" if logged_in.value else "")),
    )
