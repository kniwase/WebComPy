from webcompy.app._config import GenerateConfig, ServerConfig

server_config = ServerConfig(port=8080, dev=False, static_files_dir="static")
generate_config = GenerateConfig(dist="dist", cname="", static_files_dir="static")
