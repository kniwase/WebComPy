from webcompy.utils._environment import ENVIRONMENT as _ENVIRONMENT


if _ENVIRONMENT == "pyscript":
    from webcompy._browser._pyscript import browser  # type: ignore
else:
    browser = None
