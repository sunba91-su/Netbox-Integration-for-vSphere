from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class NetBoxConfig(BaseModel):
    url: str = ""
    token: str = Field(default="", validation_alias="NVS_NETBOX_TOKEN")
    verify_ssl: bool = True
    page_size: int = 100
    brief_mode: bool = True
    exclude_config_context: bool = True
    request_timeout: int = 120
    max_retries: int = 3

    @model_validator(mode="after")
    def check_required(self) -> NetBoxConfig:
        if not self.url:
            raise ValueError("netbox.url is required")
        if not self.token:
            raise ValueError("netbox.token is required")
        return self
