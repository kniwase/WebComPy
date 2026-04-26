from webcompy.app._config import GenerateConfig, LockfileSyncConfig, ServerConfig

server_config = ServerConfig(port=8080, dev=False)
generate_config = GenerateConfig(dist="docs", cname="webcompy.net")
lockfile_sync_config = LockfileSyncConfig(sync_group="browser")
