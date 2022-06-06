from functools import partial
import os
import pathlib
import shutil
from webcompy.cli._argparser import get_params
from webcompy.cli._pyscript_wheel import make_webcompy_app_package
from webcompy.cli._html import generate_html
from webcompy.cli._utils import (
    get_app,
    get_config,
    get_webcompy_packge_dir,
    generate_app_version,
)
from webcompy.cli._static_files import get_static_files


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

    nojekyll_path = dist_dir / ".nojekyll"
    nojekyll_path.touch()
    print(nojekyll_path)

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
    )
    for p in scripts_dir.iterdir():
        print(p)

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
