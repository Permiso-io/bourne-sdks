from __future__ import annotations

from permiso_custom_hooks import PermisoCustomHooksClient


def run_sequential_batch_jobs(client: PermisoCustomHooksClient) -> None:
    """Back-to-back runs in one process: end_run closes one job, next event uses a new run_id."""
    client.send_event("job_event", {"source": "user", "type": "text", "text": "Job A payload"})
    client.end_run()
    client.send_event("job_event", {"source": "user", "type": "text", "text": "Job B payload"})
    client.end_run()
