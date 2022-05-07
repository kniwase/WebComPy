from webcompy.brython._typing import _browser

browser = _browser if _browser.ENVIRONMENT == "browser" else None
