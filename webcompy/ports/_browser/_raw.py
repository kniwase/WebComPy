from webcompy.utils._environment import ENVIRONMENT as _ENVIRONMENT

if _ENVIRONMENT == "pyscript":
    from webcompy.ports._browser._pyscript import browser  # type: ignore
else:
    browser = None
