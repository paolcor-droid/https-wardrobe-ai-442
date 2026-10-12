"""Fail-closed network guard for the legacy single-user development API.

This is not authentication. Do not enable remote customer traffic until every
record and photo is assigned to a verified account and ownership is enforced.
"""
from ipaddress import ip_address


def allow_legacy_dev_request(client_host: str | None, production: bool) -> bool:
    if production or not client_host:
        return False
    try:
        return ip_address(client_host).is_loopback
    except ValueError:
        return False


def allow_account_preview_request(path: str, production: bool) -> bool:
    """Permit ownership-enforcing account routes in private development previews only.

    Legacy /api routes remain loopback-only. Production stays fail-closed.
    The account router still authenticates protected resources itself.
    """
    return not production and (path == "/api/account" or path.startswith("/api/account/"))
