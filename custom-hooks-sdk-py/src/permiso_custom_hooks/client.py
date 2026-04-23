"""
Client for the Permiso Custom Hooks API.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from typing import Any, Final

from .exceptions import PermisoCustomHooksError

HOOK_SOURCE_HEADER = "custom"

BOURNE_VERSION = "v2"

# Production Permiso API base URL (no trailing slash). Used when base_url is omitted from config.
_DEFAULT_CUSTOM_HOOKS_BASE_URL = "https://alb.permiso.io"

_UNSET: Final[object] = object()


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
class PermisoAgentContext:
    """
    Agent metadata sent as a top-level ``agent`` object on each request when any field is set.

    JSON keys match the API: ``systemPrompt``, ``name``, ``id`` (the latter is the agent id,
    distinct from end-user :attr:`PermisoUser.id`).
    """

    system_prompt: str | None = None
    name: str | None = None
    id: str | None = None

    def to_agent_json(self) -> dict[str, str]:
        """Build the ``agent`` object for the request body (camelCase keys)."""
        out: dict[str, str] = {}
        if self.system_prompt is not None:
            out["systemPrompt"] = self.system_prompt
        if self.name is not None:
            out["name"] = self.name
        if self.id is not None:
            out["id"] = self.id
        return out


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

    parent_run_id: str | None = None
    """
    Optional parent run ID (e.g. for a sub-agent). Sent as top-level ``parentRunId`` on every
    request next to ``runId`` so the backend can link this run to a parent run.
    """

    agent: PermisoAgentContext | None = None
    """
    Optional initial agent metadata. Sent as top-level ``agent`` when at least one field is set.
    Merged with ``system_prompt`` when that field is not ``None`` (see :attr:`system_prompt`).
    """

    system_prompt: str | None = None
    """
    Optional system prompt at the top level of config. After ``agent`` is applied, sets or
    overrides ``agent.systemPrompt`` on each request.
    """

    session_id: str | None = None
    """
    Optional session id. When set, it is attached as a top-level ``sessionId`` on every request.
    """

    user: PermisoUser | None = None
    """Optional user metadata attached as a top-level ``user`` object on every request."""

    raise_on_error: bool = False
    """
    When ``True``, :meth:`send_event` and :meth:`end_run` raise :exc:`PermisoCustomHooksError` on
    failures. When ``False`` (the default), they return ``{}`` instead; a failed :meth:`end_run`
    does not rotate ``run_id``.
    """


def _initial_agent_dict(config: PermisoCustomHooksConfig) -> dict[str, str]:
    """Merge ``config.agent`` then apply top-level ``system_prompt`` when not ``None``."""
    merged: dict[str, str] = {}
    if config.agent is not None:
        merged.update(config.agent.to_agent_json())
    if config.system_prompt is not None:
        merged["systemPrompt"] = config.system_prompt
    return merged


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
        self._parent_run_id: str | None = config.parent_run_id
        self._raise_on_error: bool = config.raise_on_error
        self._run_id: str = str(uuid.uuid4())
        self._agent: dict[str, str] = _initial_agent_dict(config)
        self._session_id: str | None = config.session_id
        self._user: PermisoUser | None = (
            PermisoUser(email=config.user.email, id=config.user.id, name=config.user.name)
            if config.user is not None
            else None
        )

    def get_run_id(self) -> str:
        """
        Return the current run ID. A new run ID is generated in the constructor and
        after every successful call to :meth:`end_run`.
        """
        return self._run_id

    def set_system_prompt(self, prompt: str | None) -> None:
        """
        Set (or clear) the system prompt included in the top-level ``agent`` object on every
        subsequent request.
        """
        if prompt is None:
            self._agent.pop("systemPrompt", None)
        else:
            self._agent["systemPrompt"] = prompt

    def set_agent(
        self,
        *,
        system_prompt: str | None | object = _UNSET,
        name: str | None | object = _UNSET,
        id: str | None | object = _UNSET,
    ) -> None:
        """
        Merge agent metadata into the client state for subsequent requests.

        Omit a keyword argument to leave that field unchanged. Pass ``None`` to clear
        ``system_prompt``, ``name``, or ``id`` from the outbound ``agent`` payload.
        """
        if system_prompt is not _UNSET:
            if system_prompt is None:
                self._agent.pop("systemPrompt", None)
            else:
                self._agent["systemPrompt"] = str(system_prompt)
        if name is not _UNSET:
            if name is None:
                self._agent.pop("name", None)
            else:
                self._agent["name"] = str(name)
        if id is not _UNSET:
            if id is None:
                self._agent.pop("id", None)
            else:
                self._agent["id"] = str(id)

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

        The request body includes ``hookEvent``, ``runId``, ``event``, ``bourneVersion``, and when
        configured ``parentRunId``, ``sessionId``, ``user``, and ``agent``.

        Args:
            event_name: Hook event name (e.g. "session_start", "my_custom_event"). Sent as
                ``hookEvent``.
            data: Optional event payload fields. Sent as the ``event`` object on the
                request body.

        Returns:
            The API response dict, or ``{}`` if ``raise_on_error`` is ``False`` and the request
            fails.

        Raises:
            PermisoCustomHooksError: When ``raise_on_error`` is ``True`` and the request fails.
        """
        try:
            return self._dispatch_hook_event(event_name, data)
        except PermisoCustomHooksError:
            if self._raise_on_error:
                raise
            return {}

    def end_run(self, stop_reason: str = "end_turn") -> dict[str, Any]:
        """
        Send a ``stop`` event for the current run, then rotate to a fresh ``run_id`` after a
        successful request.

        Args:
            stop_reason: Sent as ``stopReason`` in the stop event (default ``\"end_turn\"``).

        Returns:
            Parsed API response dict, or ``{}`` if ``raise_on_error`` is ``False`` and the stop
            request fails (in that case ``run_id`` is not rotated).

        Raises:
            PermisoCustomHooksError: When ``raise_on_error`` is ``True`` and the stop request fails.
        """
        try:
            response = self._dispatch_hook_event(
                "stop",
                {"source": "stop", "stopReason": stop_reason},
            )
            self._run_id = str(uuid.uuid4())
            return response
        except PermisoCustomHooksError:
            if self._raise_on_error:
                raise
            return {}

    def _dispatch_hook_event(
        self,
        event_name: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "hookEvent": event_name,
            "runId": self._run_id,
            "event": data or {},
            "bourneVersion": BOURNE_VERSION,
        }
        if self._parent_run_id is not None:
            body["parentRunId"] = self._parent_run_id
        if self._session_id is not None:
            body["sessionId"] = self._session_id
        if self._user is not None and self._user.has_any_field():
            body["user"] = self._user.to_dict()
        if self._agent:
            body["agent"] = dict(self._agent)

        url = f"{self._base_url}/hooks"
        try:
            payload = json.dumps(body).encode("utf-8")
        except (TypeError, ValueError) as e:
            raise PermisoCustomHooksError(
                f"Failed to serialize request body: {e}",
            ) from e

        req = urllib.request.Request(
            url,
            data=payload,
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
            parsed: dict[str, Any] = json.loads(raw_body) if raw_body else {}
        except json.JSONDecodeError as e:
            raise PermisoCustomHooksError(
                "Invalid JSON response from Custom Hooks API",
                status=status,
                body=raw_body,
            ) from e

        return parsed
