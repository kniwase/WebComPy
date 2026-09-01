"""Opt-in adapters backed by heavy third-party dependencies.

Modules in this package are never imported by the framework itself.
Applications that add the optional dependency import the adapter module
directly and register their rules during startup.
"""
