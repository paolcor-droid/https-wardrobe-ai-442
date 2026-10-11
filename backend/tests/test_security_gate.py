from services.security_gate import allow_legacy_dev_request


def test_local_legacy_development_only():
    assert allow_legacy_dev_request("127.0.0.1", False)
    assert allow_legacy_dev_request("::1", False)
    for remote in ("8.8.8.8", "192.168.0.12", "10.0.0.1", "172.16.0.2", "localhost", None, ""):
        assert not allow_legacy_dev_request(remote, False)


def test_production_blocks_everyone_even_loopback():
    assert not allow_legacy_dev_request("127.0.0.1", True)
    assert not allow_legacy_dev_request("::1", True)
