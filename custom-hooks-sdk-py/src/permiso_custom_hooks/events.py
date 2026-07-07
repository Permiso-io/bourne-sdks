"""
Typed hook event payloads for the ``event`` field on Custom Hooks requests.

Matches the Bourne v2 content-block schema (see package README).
"""

from __future__ import annotations

from typing import Literal, TypedDict, Union


class _ToolResultRequired(TypedDict):
    type: Literal["tool_result"]
    toolUseId: str


class _UserToolResultRequired(_ToolResultRequired):
    source: Literal["user"]


class _AgentToolResultRequired(_ToolResultRequired):
    source: Literal["agent"]


class _ToolResultOptional(TypedDict, total=False):
    """Optional fields on ``tool_result`` events."""

    name: str
    content: str
    isError: bool
    eventId: str
    timestamp: Union[int, str]


class _AgentToolResultOptional(TypedDict, total=False):
    model: str
    temperature: float
    maxTokens: int
    topP: float
    topK: int


class UserToolResultEvent(_UserToolResultRequired, _ToolResultOptional):
    """User-originated ``tool_result`` content block."""


class AgentToolResultEvent(_AgentToolResultRequired, _ToolResultOptional, _AgentToolResultOptional):
    """Agent-originated ``tool_result`` content block."""


ToolResultEvent = Union[UserToolResultEvent, AgentToolResultEvent]
"""``tool_result`` event payload (``source: \"user\"`` or ``\"agent\"``)."""
