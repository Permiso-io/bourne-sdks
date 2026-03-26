"""
Client for the Permiso Custom Hooks API.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from typing import Any

from .exceptions import PermisoCustomHooksError

HOOK_SOURCE_HEADER = "custom"

BOURNE_VERSION = "v2"

# Production Permiso API base URL (no trailing slash). Used when base_url is omitted from config.
_DEFAULT_CUSTOM_HOOKS_BASE_URL = "https://alb.permiso.io"


@dataclass
class PermisoUser:
    """
    User metadata attached to each request when set via :meth:`PermisoCustomHooksClient.set_user`
    or the ``user`` config option. All fields are optional; ``set_user`` merges partial updates
    into the current value.
    """

    email: str | None = None
    """Email address of the end user."""

    id: str | None = None
    """Stable identifier of the end user."""

    name: str | None = None
    """Display name of the end user."""

    def to_dict(self) -> dict[str, Any]:
        """Return a dict containing only fields that are not ``None``."""
        result: dict[str, Any] = {}
        if self.email is not None:
            result["email"] = self.email
        if self.id is not None:
            result["id"] = self.id
        if self.name is not None:
            result["name"] = self.name
        return result

    def has_any_field(self) -> bool:
        """Return True if at least one field is set (not ``None``)."""
        return self.email is not None or self.id is not None or self.name is not None


@dataclass
class PermisoCustomHooksConfig:
    """Configuration for the Permiso Custom Hooks client."""

    api_key: str
    """API key (secret) for authentication. Use the secret from your Permiso agent (A2M Keys)."""

    base_url: str | None = None
    """
    Base URL of the Permiso API (without ``/hooks``). The client POSTs to ``{base_url}/hooks``.
    Defaults to ``https://alb.permiso.io`` when omitted.
    """

    system_prompt: str | None = None
    """
    Optional system prompt. When set, the SDK emits a dedicated ``system_prompt`` event
    before the first event of each run (including after :meth:`PermisoCustomHooksClient.end_run`
    rotates the run id).
    """

    session_id: str | None = None
    """Optional session id. When set, it is attached as a top-level ``sessionId`` on every request."""

    user: PermisoUser | None = None
    """Optional user metadata attached as a top-level ``user`` object on every request."""


class PermisoCustomHooksClient:
    """
    Client for the Permiso Custom Hooks API.

    Manages a run ID automatically: the constructor generates an initial ``run_id`` that is
    sent on every request. Call :meth:`end_run` to send a ``stop`` event and rotate to a
    fresh ``run_id`` for any subsequent calls.
    """

    def __init__(self, config: PermisoCustomHooksConfig) -> None:
        base = (config.base_url or _DEFAULT_CUSTOM_HOOKS_BASE_URL).rstrip("/")
        self._base_url = base
        self._api_key = config.api_key
        self._run_id: str = str(uuid.uuid4())
        self._system_prompt: str | None = config.system_prompt
        self._session_id: str | None = config.session_id
        self._user: PermisoUser | None = (
            PermisoUser(email=config.user.email, id=config.user.id, name=config.user.name)
            if config.user is not None
            else None
        )
        self._system_prompt_sent_for_current_run: bool = False

    def get_run_id(self) -> str:
        """
        Return the current run ID. A new run ID is generated in the constructor and
        after every call to :meth:`end_run`.
        """
        return self._run_id

    def set_system_prompt(self, prompt: str | None) -> None:
        """
        Set (or clear) the system prompt. When set, the SDK emits a dedicated
        ``system_prompt`` event before the first event of each run. If the first event of
        the current run has already been sent, the prompt will instead be emitted before
        the first event of the next run (after :meth:`end_run`).
        """
        self._system_prompt = prompt

    def set_session_id(self, session_id: str | None) -> None:
        """
        Set (or clear) the session ID. When set, it is attached as a top-level ``sessionId``
        field on every subsequent request.
        """
        self._session_id = session_id

    def set_user(self, user: PermisoUser) -> None:
        """
        Merge partial user metadata into the client's user state. Callers can set just one
        of ``email``, ``id``, or ``name`` without clobbering the others. The resulting
        user object is attached as a top-level ``user`` field on every subsequent request.
        """
        current = self._user or PermisoUser()
        if user.email is not None:
            current.email = user.email
        if user.id is not None:
            current.id = user.id
        if user.name is not None:
            current.name = user.name
        self._user = current

    def send_event(
        self,
        event_name: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Send a hook event to the Permiso Custom Hooks endpoint.

        The request body has the shape ``{ hookEvent, runId, event, bourneVersion }``: ``hookEvent`` is the
        event name, ``runId`` is the current run ID at the top level of the body, and
        ``event`` is an object containing the optional payload fields from ``data``. When
        configured, ``sessionId`` and ``user`` are also attached at the top level.

        If a system prompt is set and has not yet been emitted for the current run, a
        ``system_prompt`` event is sent first.

        Args:
            event_name: Hook event name (e.g. "session_start", "my_custom_event"). Sent as
                ``hookEvent``.
            data: Optional event payload fields. Sent as the ``event`` object on the
                request body.

        Returns:
            The API response dict.

        Raises:
            PermisoCustomHooksError: On non-2xx or network/parse failure.
        """
        if self._system_prompt is not None and not self._system_prompt_sent_for_current_run:
            self._system_prompt_sent_for_current_run = True
            self.send_event(
                "system_prompt",
                {"source": "system", "type": "text", "text": self._system_prompt},
            )

        body: dict[str, Any] = {
            "hookEvent": event_name,
            "runId": self._run_id,
            "event": data or {},
            "bourneVersion": BOURNE_VERSION,
        }
        if self._session_id is not None:
            body["sessionId"] = self._session_id
        if self._user is not None and self._user.has_any_field():
            body["user"] = self._user.to_dict()

        url = f"{self._base_url}/hooks"
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-api-key": self._api_key,
                "X-Hook-Source": HOOK_SOURCE_HEADER,
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req) as resp:
                raw_body = resp.read().decode("utf-8")
                status = resp.status
        except urllib.error.HTTPError as e:
            raw_body = e.read().decode("utf-8") if e.fp else ""
            raise PermisoCustomHooksError(
                f"Custom Hooks API error: {e.code} {e.reason}",
                status=e.code,
                body=raw_body,
            ) from e
        except urllib.error.URLError as e:
            raise PermisoCustomHooksError(
                f"Request failed: {e.reason}",
            ) from e

        if status < 200 or status >= 300:
            raise PermisoCustomHooksError(
                f"Custom Hooks API error: {status}",
                status=status,
                body=raw_body,
            )

        try:
            parsed = json.loads(raw_body) if raw_body else {}
        except json.JSONDecodeError as e:
            raise PermisoCustomHooksError(
                "Invalid JSON response from Custom Hooks API",
                status=status,
                body=raw_body,
            ) from e

        return parsed

    def end_run(self) -> dict[str, Any]:
        """
        Send a ``stop`` event for the current run, then rotate to a fresh ``run_id`` so any
        subsequent calls to :meth:`send_event` start a new run.
        """
        response = self.send_event("stop", {"source": "stop"})
        self._run_id = str(uuid.uuid4())
        self._system_prompt_sent_for_current_run = False
        return response
