import asyncio

from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.router import use_router

_auth_state = {"authenticated": False}


async def auth_guard(from_path: str, to_path: str):
    if to_path.split("?")[0].strip("/") == "admin":
        await asyncio.sleep(0.05)
        if not _auth_state["authenticated"]:
            return "/login"
    return None


@define_component
def GuardLoginPage(context: ComponentContext[None]):
    context.set_title("Login - E2E")
    router = use_router()

    def _login(ev):
        _auth_state["authenticated"] = True
        router.__set_path__("/admin", None)

    return html.DIV(
        {"data-testid": "login-page"},
        html.H2({}, "Login"),
        html.BUTTON({"data-testid": "login-button", "@click": _login}, "Log in"),
    )


@define_component
def GuardAdminPage(context: ComponentContext[None]):
    context.set_title("Admin - E2E")
    return html.DIV({"data-testid": "admin-page"}, html.H2({}, "Protected Admin"))
