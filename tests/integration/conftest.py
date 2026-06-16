"""Shared fixtures for integration tests using vcrpy.

VCR cassettes are stored in tests/integration/cassettes/.
To record new cassettes:
  1. Set record_mode=RecordMode.NONE to RecordMode.ALL in the fixture below
  2. Run the test once with a live NetBox instance
  3. Cassette files are auto-generated in cassettes/
  4. Reset record_mode back to RecordMode.NONE for CI
"""

from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

import pytest
import vcr
from vcr.record_mode import RecordMode

from netbox_vsphere_sync.domain.model.config import NetBoxConfig
from netbox_vsphere_sync.infrastructure.netbox.client import NetBoxClient

CASSETTE_DIR = Path(__file__).parent / "cassettes"

# Filter sensitive headers from recorded cassettes
CASSETTE_FILTERED_HEADERS = ["Authorization", "X-NetBox-Token", "Cookie"]


@pytest.fixture()
def vcr_cassette_dir() -> Path:
    """Return the directory for VCR cassette files."""
    return CASSETTE_DIR


@pytest.fixture()
def netbox_config(monkeypatch: pytest.MonkeyPatch) -> NetBoxConfig:
    """Create a NetBoxConfig for integration tests.

    Uses env vars NVS_NETBOX_URL and NVS_NETBOX_TOKEN if set,
    otherwise falls back to localhost defaults for cassette replay.
    """
    monkeypatch.setenv(
        "NVS_NETBOX_URL",
        os.environ.get("NVS_NETBOX_URL", "http://localhost:8000"),
    )
    monkeypatch.setenv(
        "NVS_NETBOX_TOKEN",
        os.environ.get("NVS_NETBOX_TOKEN", "test-token-integration"),
    )
    return NetBoxConfig(
        url=os.environ.get("NVS_NETBOX_URL", "http://localhost:8000"),
        token=os.environ.get("NVS_NETBOX_TOKEN", "test-token-integration"),
        verify_ssl=False,
        max_retries=0,
    )


def _get_cassette_path(request: pytest.FixtureRequest) -> Path:
    """Build cassette path from the test node ID."""
    test_id = request.node.nodeid.replace("::", "_").replace("/", "_").replace(" ", "_")
    return CASSETTE_DIR / f"{test_id}.yaml"


@pytest.fixture()
def netbox_client(
    netbox_config: NetBoxConfig,
    request: pytest.FixtureRequest,
) -> Generator[NetBoxClient, None, None]:
    """Create a connected NetBoxClient for integration tests.

    Skips the test if no cassette file exists (for CI without a live NetBox).
    Uses VCR to record/replay HTTP interactions.
    """
    cassette_file = _get_cassette_path(request)

    if not cassette_file.exists():
        pytest.skip(f"No cassette file found: {cassette_file.name}")

    my_vcr = vcr.VCR(
        record_mode=RecordMode.NONE,
        cassette_library_dir=str(CASSETTE_DIR),
        path_transformer=vcr.VCR.ensure_suffix(".yaml"),
        filter_headers=CASSETTE_FILTERED_HEADERS,
    )

    with my_vcr.use_cassette(str(cassette_file)):
        client = NetBoxClient(netbox_config)
        client.connect()
        yield client
