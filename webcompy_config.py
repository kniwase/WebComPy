from webcompy.cli import WebComPyConfig

config = WebComPyConfig(
    app_package="docs_src",
    dist="docs",
    base="/WebComPy",
    dependencies=[
        "numpy",
        "matplotlib",
    ],
)
