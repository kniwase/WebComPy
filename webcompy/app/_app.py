from webcompy.components import ComponentGenerator
from webcompy.router import Router
from webcompy.app._root_component import AppDocumentRoot


class WebComPyApp:
    _root: AppDocumentRoot
    _router: Router | None

    def __init__(
        self,
        *,
        root_component: ComponentGenerator[None],
        router: Router | None = None,
    ) -> None:
        self._root = AppDocumentRoot(root_component, router)

    @property
    def __render__(self):
        return self._root.render

    def __generate__(self):
        import pathlib
        import os
        import shutil

        dist = pathlib.Path.cwd() / "dist"
        if dist.exists():
            shutil.rmtree(dist)
        os.mkdir(dist)
        if len(self._root.routes) and self._root.router_mode == "history":
            for path in self._root.routes:
                page_dir = dist / path
                if not page_dir.exists():
                    os.makedirs(page_dir)
                html = self._root.render_html(path, indent=0)
                with (page_dir / "index.html").open("w", encoding="utf8") as f:
                    f.write(html)
        else:
            html = self._root.render_html(indent=0)
            (dist / "index.html").open("w", encoding="utf8").write(html)
