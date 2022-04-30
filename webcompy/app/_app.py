from webcompy.components import ComponentGenerator
from webcompy.router import Router
from webcompy.app._root_component import AppDocumentRoot


class WebComPyApp:
    _root: AppDocumentRoot
    _router: Router | None

    def __init__(
        self, *, root_component: ComponentGenerator[None], router: Router | None = None
    ) -> None:
        self._root_component = root_component
        self._router = router

    def init(self):
        self._root = AppDocumentRoot(self._root_component, self._router)

    def generate(self):
        import pathlib
        import os
        import shutil

        dist = pathlib.Path.cwd() / "dist"
        if dist.exists():
            shutil.rmtree(dist)
        os.mkdir(dist)
        if len(self._root.routes):
            for path in self._root.routes:
                html = self._root.render_html(path, indent=0)
                page_dir = dist / path
                if not page_dir.exists():
                    os.makedirs(page_dir)
                with (page_dir / "index.html").open("w", encoding="utf8") as f:
                    f.write(html)
        else:
            html = self._root.render_html(indent=0)
            (dist / "index.html").open("w").write(html)
