"""
Permiso Custom Hooks SDK — send hook events with automatic run handling.
"""

from .client import (
    PermisoAgentContext,
    PermisoCustomHooksClient,
    PermisoCustomHooksConfig,
    PermisoUser,
)
from .exceptions import PermisoCustomHooksError

__all__ = [
    "PermisoAgentContext",
    "PermisoCustomHooksClient",
    "PermisoCustomHooksConfig",
    "PermisoCustomHooksError",
    "PermisoUser",
]
__version__ = "0.1.2"
