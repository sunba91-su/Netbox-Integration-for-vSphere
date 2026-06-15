from __future__ import annotations

from pydantic import BaseModel


class BootstrapConfig(BaseModel):
    enabled: bool = True
    create_manufacturer: bool = True
    create_device_role: bool = True
    create_cluster_type: bool = True
    create_custom_fields: bool = True
