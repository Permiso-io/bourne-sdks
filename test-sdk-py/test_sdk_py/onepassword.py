import subprocess


def get_onepassword_secret(
    vault_uuid: str, item_uuid: str, field_name: str
) -> str:
    reference = f"op://{vault_uuid}/{item_uuid}/{field_name}"
    field = subprocess.run(
        ["op", "read", reference], capture_output=True, check=True
    )
    field = field.stdout.decode("utf-8")
    field = field.strip()
    return field
