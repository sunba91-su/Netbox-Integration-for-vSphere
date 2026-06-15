from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, field_validator
from pydantic_core.core_schema import ValidationInfo


class VlanAllocationConfig(BaseModel):
    strategy: Literal["from_portgroup", "reserved_range", "auto_allocate"] = "from_portgroup"
    range_start: int = 3000
    range_end: int = 3999

    @field_validator("range_end")
    @classmethod
    def check_range(cls, v: int, info: ValidationInfo) -> int:
        range_start: int = info.data.get("range_start", 3000)  # type: ignore[no-untyped-call]
        if v <= range_start:
            raise ValueError("range_end must be greater than range_start")
        return v


class IpAddressRoleRule(BaseModel):
    pattern: str = ""
    role: str | None = None
