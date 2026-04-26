from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.signal import Signal


@define_component
def BundledDepsPage(context: ComponentContext[None]):
    context.set_title("Bundled Deps - E2E")

    aiofiles_status = Signal("pending")
    h11_status = Signal("pending")

    def check_aiofiles(_):
        try:
            import aiofiles

            aiofiles_status.value = f"ok:{getattr(aiofiles, '__version__', 'unknown')}"
        except Exception as e:
            aiofiles_status.value = f"error:{e}"

    def check_h11(_):
        try:
            import h11

            h11_status.value = f"ok:{getattr(h11, '__version__', 'unknown')}"
        except Exception as e:
            h11_status.value = f"error:{e}"

    return html.DIV(
        {"data-testid": "bundled-deps-page"},
        html.H2({}, "Bundled Deps Tests"),
        html.DIV(
            {},
            html.SPAN({"data-testid": "aiofiles-status"}, aiofiles_status),
            html.BUTTON({"data-testid": "check-aiofiles-btn", "@click": check_aiofiles}, "Check aiofiles"),
        ),
        html.DIV(
            {},
            html.SPAN({"data-testid": "h11-status"}, h11_status),
            html.BUTTON({"data-testid": "check-h11-btn", "@click": check_h11}, "Check h11"),
        ),
    )
