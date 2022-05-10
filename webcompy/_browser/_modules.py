from webcompy.utils._environment import ENVIRONMENT as _ENVIRONMENT


if _ENVIRONMENT == "pyscript":
    from webcompy._browser._pyscript import browser_pyscript

    browser = browser_pyscript
    browser_brython = None
elif _ENVIRONMENT == "brython":
    from webcompy._browser._brython import browser_brython

    browser = browser_brython
    browser_pyscript = None
else:
    browser_pyscript = None
    browser_brython = None
    browser = None
