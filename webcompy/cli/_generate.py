from functools import partial
import os
import pathlib
import shutil
from webcompy.cli._argparser import get_params
from webcompy.cli._pyscript_wheel import make_webcompy_app_package_pyscript
from webcompy.cli._brython_cli import make_webcompy_app_package_brython
from webcompy.cli._html import generate_html
from webcompy.cli._utils import (
    get_app,
    get_config,
    get_webcompy_packge_dir,
    generate_app_version,
)


def generate_static_site():
    config = get_config()
    app = get_app(config)
    _, args = get_params()
    config = get_config()
    dist = config.dist if args.get("dist") is None else args["dist"]
    app_version = generate_app_version()

    dist_dir = pathlib.Path(dist).absolute()
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    os.mkdir(dist_dir)

    scripts_dir = dist_dir / "webcompy-app-package"
    os.mkdir(scripts_dir)
    make_webcompy_app_package = (
        make_webcompy_app_package_pyscript
        if config.environment == "pyscript"
        else make_webcompy_app_package_brython
    )
    make_webcompy_app_package(
        scripts_dir,
        get_webcompy_packge_dir(),
        pathlib.Path(f"./{config.app_package}").absolute(),
        app_version,
    )

    html_generator = partial(generate_html, config, False, True, app_version)
    if app.__component__.router_mode == "history" and app.__component__.routes:
        for p, _, _, _, page in app.__component__.routes:
            if path_params := page.get("path_params"):
                paths = {p.format(**params) for params in path_params}
            else:
                paths = {p}
            for path in paths:
                if not (path_dir := dist_dir / path).exists():
                    os.makedirs(path_dir)
                app.__component__.set_path(path)
                html = html_generator(app)
                html_path = path_dir / "index.html"
                html_path.open("w", encoding="utf8").write(html)
                print(html_path)
        app.__component__.set_path("//:404://")
        html = html_generator(app)
        html_path = dist_dir / "404.html"
        html_path.open("w", encoding="utf8").write(html)
        print(html_path)
    else:
        app.__component__.set_path("/")
        html = html_generator(app)
        html_path = dist_dir / "index.html"
        html_path.open("w", encoding="utf8").write(html)
        print(html_path)
    print("done")
