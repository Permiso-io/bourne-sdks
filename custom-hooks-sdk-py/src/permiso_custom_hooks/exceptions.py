"""
Custom Hooks API errors.
"""

from __future__ import annotations


class PermisoCustomHooksError(Exception):
    """
    Raised when the Custom Hooks API returns a non-2xx response or the request fails.
    """

    def __init__(
        self,
        message: str,
        status: int | None = None,
        body: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status = status
        self.body = body
