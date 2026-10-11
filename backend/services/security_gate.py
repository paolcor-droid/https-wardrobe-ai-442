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
