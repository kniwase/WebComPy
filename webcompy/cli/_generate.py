import os
import pathlib
import shutil
from functools import partial

from webcompy.app._app import WebComPyApp
from webcompy.cli._argparser import get_params
from webcompy.cli._config import WebComPyConfig
from webcompy.cli._html import generate_html
from webcompy.cli._static_files import get_static_files
from webcompy.cli._utils import (
    generate_app_version,
    get_app,
    get_config,
    get_webcompy_packge_dir,
)
from webcompy.cli._wheel_builder import make_webcompy_app_package


def generate_static_site(app: WebComPyApp | None = None):
    if app is None:
        config = get_config()
        app = get_app(config)
    else:
        config = _build_config_from_app(app)

    _, args = get_params()
    with app.di_scope:
        dist = config.dist if args.get("dist") is None else args["dist"]
        app_version = generate_app_version()

        dist_dir = pathlib.Path(dist).absolute()
        if dist_dir.exists():
            shutil.rmtree(dist_dir)
        os.mkdir(dist_dir)

        nojekyll_path = dist_dir / ".nojekyll"
        nojekyll_path.touch()
        print(nojekyll_path)

        if config.cname:
            cname_path = dist_dir / "CNAME"
            cname_path.open("w", encoding="utf8").write(config.cname)
            print(cname_path)

        static_files_dir = config.static_files_dir_path.absolute()
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
            config.app_package_path,
            app_version,
            config.assets,
        )
        for p in scripts_dir.iterdir():
            print(p)

        html_generator = partial(generate_html, config, False, True, app_version, config.app_package_path.name)
        if app.router_mode == "history" and app.routes:
            for p, _, _, _, page in app.routes:
                paths = (
                    {p.format(**params) for params in path_params} if (path_params := page.get("path_params")) else {p}
                )
                for path in paths:
                    if not (path_dir := dist_dir / path).exists():
                        os.makedirs(path_dir)
                    app.set_path(path)
                    html = html_generator(app)
                    html_path = path_dir / "index.html"
                    html_path.open("w", encoding="utf8").write(html)
                    print(html_path)
            app.set_path("//:404://")
            html = html_generator(app)
            html_path = dist_dir / "404.html"
            html_path.open("w", encoding="utf8").write(html)
            print(html_path)
        else:
            app.set_path("/")
            html = html_generator(app)
            html_path = dist_dir / "index.html"
            html_path.open("w", encoding="utf8").write(html)
            print(html_path)

        print("done")


def _build_config_from_app(app: WebComPyApp) -> WebComPyConfig:
    app_config = app.config
    return WebComPyConfig(
        app_package=app_config.app_package_path,
        base=app_config.base_url,
        dependencies=app_config.dependencies,
        assets=app_config.assets,
    )
