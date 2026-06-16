"""Integration test placeholder — verifies test infrastructure works."""

from __future__ import annotations

import pytest

from netbox_vsphere_sync.infrastructure.netbox.client import NetBoxClient


@pytest.mark.integration
def test_netbox_client_fixture(netbox_client: NetBoxClient) -> None:
    """Verify the netbox_client fixture creates a connected client."""
    assert netbox_client is not None
    assert netbox_client._api is not None
