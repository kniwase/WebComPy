from pathlib import Path
from webcompy.cli import WebComPyConfig

config = WebComPyConfig(
    app_package=Path(__file__).parent / "docs_src",
    dist="docs",
    base="/WebComPy",
    dependencies=[
        "numpy",
        "matplotlib",
    ],
)
