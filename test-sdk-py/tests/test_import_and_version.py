import permiso_custom_hooks as pkg


def test_version_and_public_exports() -> None:
    assert isinstance(pkg.__version__, str) and len(pkg.__version__) >= 3
    for name in (
        "PermisoCustomHooksClient",
        "PermisoCustomHooksConfig",
        "PermisoUser",
        "PermisoAgentContext",
        "PermisoCustomHooksError",
    ):
        assert hasattr(pkg, name)
