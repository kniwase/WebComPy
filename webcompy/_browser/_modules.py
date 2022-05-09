from webcompy.utils._environment import ENVIRONMENT as _ENVIRONMENT


if _ENVIRONMENT == "brython":
    from webcompy._browser._brython import _browser as browser  # type: ignore
else:
    browser = None
