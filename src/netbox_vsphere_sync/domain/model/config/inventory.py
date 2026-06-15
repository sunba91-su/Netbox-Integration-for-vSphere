from __future__ import annotations

from pydantic import BaseModel


class InventoryRoleConfig(BaseModel):
    storage: str = "Storage"
