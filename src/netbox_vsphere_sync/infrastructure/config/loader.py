from __future__ import annotations

import os
from pathlib import Path

import yaml

from netbox_vsphere_sync.domain.exceptions import ConfigError
from netbox_vsphere_sync.domain.model.config import AppConfig


class ConfigLoader:
    def __init__(self, config_path: str | Path) -> None:
        self._config_path = Path(config_path)

    def load(self) -> AppConfig:
        if not self._config_path.exists():
            raise ConfigError(f"Config file not found: {self._config_path}")

        raw = self._read_yaml()
        config = AppConfig.model_validate(raw)
        return config

    def _read_yaml(self) -> dict:
        with open(self._config_path) as f:
            data: dict = yaml.safe_load(f) or {}

        def interpolate_env(value: object) -> object:
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                env_var = value[2:-1]
                default = None
                if ":-" in env_var:
                    env_var, default = env_var.split(":-", 1)
                resolved = os.environ.get(env_var, default)
                if resolved is None:
                    raise ConfigError(
                        f"Environment variable {env_var} is not set "
                        f"and no default provided in config"
                    )
                return resolved
            if isinstance(value, dict):
                return {k: interpolate_env(v) for k, v in value.items()}
            if isinstance(value, list):
                return [interpolate_env(v) for v in value]
            return value

        return interpolate_env(data)  # type: ignore[no-any-return]
