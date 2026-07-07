"""
Permiso Custom Hooks SDK — send hook events with automatic run handling.
"""

from .client import (
    PermisoAgentContext,
    PermisoCustomHooksClient,
    PermisoCustomHooksConfig,
    PermisoUser,
)
from .events import AgentToolResultEvent, ToolResultEvent, UserToolResultEvent
from .exceptions import PermisoCustomHooksError

__all__ = [
    "AgentToolResultEvent",
    "PermisoAgentContext",
    "PermisoCustomHooksClient",
    "PermisoCustomHooksConfig",
    "PermisoCustomHooksError",
    "PermisoUser",
    "ToolResultEvent",
    "UserToolResultEvent",
]
__version__ = "0.1.5"
