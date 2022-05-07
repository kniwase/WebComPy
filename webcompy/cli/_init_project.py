import os
import pathlib
import shutil
import sys
from webcompy.cli._utils import get_webcompy_packge_dir


def _get_files(path: pathlib.Path, suffix: str) -> list[str]:
    ret: list[str] = []
    if path.is_dir():
        for p in path.iterdir():
            ret.extend(_get_files(p, suffix))
    elif path.suffix == suffix:
        ret.append(str(path))
    return ret


def init_project():
    template_data_dir = (
        pathlib.Path(get_webcompy_packge_dir()) / "cli" / "template_data"
    )
    cwd = pathlib.Path().cwd().absolute()
    filepath_pairs = [
        (
            filepath,
            cwd / str(filepath).replace(str(template_data_dir), "").lstrip(os.sep),
        )
        for filepath in map(pathlib.Path, _get_files(template_data_dir, ".py"))
    ]

    files_exist = [p for _, p in filepath_pairs if p.exists()]
    if files_exist:
        for p in files_exist:
            print(p)
        while True:
            ans = input("Some files already exist. Will you overwrite them? (y/N): ")
            if len(ans) == 0 or (ans.isalpha() and ans.lower() in {"y", "n"}):
                if len(ans) == 0 or ans.lower() == "n":
                    sys.exit()
                else:
                    break
            else:
                continue
    for template_filepath, project_filepath in filepath_pairs:
        if not project_filepath.parent.exists():
            os.makedirs(project_filepath.parent)
        if project_filepath.exists():
            os.remove(project_filepath)
        shutil.copy(template_filepath, project_filepath)
        print(project_filepath)
