import os
import pathlib
import shutil
from functools import partial

from webcompy.app._app import WebComPyApp
from webcompy.app._config import GenerateConfig
from webcompy.cli._argparser import get_params
from webcompy.cli._html import generate_html
from webcompy.cli._static_files import get_static_files
from webcompy.cli._utils import (
    discover_app,
    generate_app_version,
    get_generate_config,
    get_webcompy_packge_dir,
)
from webcompy.cli._wheel_builder import make_webcompy_app_package


def generate_static_site(app: WebComPyApp | None = None, generate_config: GenerateConfig | None = None):
    _, args = get_params()
    if app is None:
        app_import_path = args.get("app")
        app = discover_app(app_import_path)
    if generate_config is None:
        generate_config = get_generate_config()

    with app.di_scope:
        dist = generate_config.dist if args.get("dist") is None else args["dist"]
        app_version = generate_app_version()

        dist_dir = pathlib.Path(dist).absolute()
        if dist_dir.exists():
            shutil.rmtree(dist_dir)
        os.mkdir(dist_dir)

        nojekyll_path = dist_dir / ".nojekyll"
        nojekyll_path.touch()
        print(nojekyll_path)

        if generate_config.cname:
            cname_path = dist_dir / "CNAME"
            cname_path.open("w", encoding="utf8").write(generate_config.cname)
            print(cname_path)

        static_files_dir = generate_config.static_files_dir_path.absolute()
        for relative_path in get_static_files(static_files_dir):
            src = static_files_dir / relative_path
            dst = dist_dir / relative_path
            if not (parent := dst.parent).exists():
                os.makedirs(parent)
            shutil.copy(src, dst)
            print(dst)

        scripts_dir = dist_dir / "_webcompy-app-package"
        os.mkdir(scripts_dir)
        make_webcompy_app_package(
            scripts_dir,
            get_webcompy_packge_dir(),
            app.config.app_package_path,
            app_version,
            app.config.assets,
        )
        for p in scripts_dir.iterdir():
            print(p)

        html_generator = partial(generate_html, app, False, True, app_version, app.config.app_package_path.name)
        if app.router_mode == "history" and app.routes:
            for p, _, _, _, page in app.routes:
                paths = (
                    {p.format(**params) for params in path_params} if (path_params := page.get("path_params")) else {p}
                )
                for path in paths:
                    if not (path_dir := dist_dir / path).exists():
                        os.makedirs(path_dir)
                    app.set_path(path)
                    html = html_generator()
                    html_path = path_dir / "index.html"
                    html_path.open("w", encoding="utf8").write(html)
                    print(html_path)
            app.set_path("//:404://")
            html = html_generator()
            html_path = dist_dir / "404.html"
            html_path.open("w", encoding="utf8").write(html)
            print(html_path)
        else:
            app.set_path("/")
            html = html_generator()
            html_path = dist_dir / "index.html"
            html_path.open("w", encoding="utf8").write(html)
            print(html_path)

        print("done")
