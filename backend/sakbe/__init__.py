"""SakbeLab: server, CLI and Python SDK.

`from sakbe import Lab` loads only the SDK (standard library + PyYAML), so it
works on any machine without the server dependencies.
"""

__version__ = "0.1.0"


def __getattr__(name: str):
    if name in ("Lab", "Node", "Interface", "SakbeError"):
        from sakbe import sdk

        return getattr(sdk, name)
    raise AttributeError(name)
