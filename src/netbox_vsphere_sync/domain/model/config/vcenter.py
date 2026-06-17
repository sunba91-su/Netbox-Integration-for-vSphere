from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class VCenterConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    host: str = ""
    username: str = Field(default="", validation_alias="NVS_VCENTER_USERNAME")
    password: str = Field(default="", validation_alias="NVS_VCENTER_PASSWORD")
    verify_ssl: bool = True

    @model_validator(mode="after")
    def check_required(self) -> VCenterConfig:
        if not self.host:
            raise ValueError("vcenter.host is required")
        if not self.username:
            raise ValueError("vcenter.username is required")
        if not self.password:
            raise ValueError("vcenter.password is required")
        return self
