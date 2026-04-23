from __future__ import annotations

from permiso_custom_hooks import PermisoCustomHooksClient, PermisoUser


def run_session_user_handoff(client: PermisoCustomHooksClient) -> None:
    """One run: anonymous event, then set_user, then end_run and a second run."""
    client.send_event(
        "turn_start",
        {"source": "user", "type": "text", "text": "Hello"},
    )
    client.set_user(PermisoUser(id="user-7", name="NewLogin"))
    client.send_event(
        "post_auth",
        {
            "source": "user",
            "type": "text",
            "text": "Now I'm logged in; continue.",
        },
    )
    client.end_run(stop_reason="end_turn")
    client.send_event(
        "turn_start",
        {
            "source": "user",
            "type": "text",
            "text": "Message on fresh run",
        },
    )
    client.end_run()
