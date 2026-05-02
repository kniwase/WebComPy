from webcompy.app._config import GenerateConfig, LockfileSyncConfig, ServerConfig

server_config = ServerConfig(port=8080, dev=False, static_files_dir="static")
generate_config = GenerateConfig(dist="docs", cname="webcompy.net", static_files_dir="static")
lockfile_sync_config = LockfileSyncConfig(sync_group="browser")
