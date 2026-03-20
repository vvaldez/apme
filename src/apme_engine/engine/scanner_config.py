"""ARI scanner configuration: Config dataclass, defaults, and target-type constants."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import cast

import yaml

from .models import LoadType, YAMLDict

ARI_CONFIG_PATH = os.getenv("ARI_CONFIG_PATH")
default_config_path = ARI_CONFIG_PATH or os.path.expanduser("~/.ari/config")
default_data_dir = os.path.join("/tmp", "ari-data")
default_rules_dir = os.path.join(os.path.dirname(__file__), "rules")
default_log_level = "info"
default_rules: list[str] = []
default_disable_default_rules = False
default_logger_key = "ari"


@dataclass
class Config:
    """ARI scanner configuration loaded from file and environment.

    Attributes:
        path: Path to the config file.
        data_dir: Directory for ARI data (collections, roles, etc.).
        rules_dir: Directory containing rule definitions.
        logger_key: Logger channel identifier.
        log_level: Logging level (e.g., info, debug).
        rules: List of rule IDs or paths to enable.
        disable_default_rules: If True, do not load default rules from rules_dir.

    """

    path: str = ""

    data_dir: str = ""
    rules_dir: str = ""
    logger_key: str = ""
    log_level: str = ""
    rules: list[str] = field(default_factory=list)
    disable_default_rules: bool = False

    _data: YAMLDict = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Load config from file and env, then populate defaults.

        Raises:
            ValueError: If config file fails to load.
        """
        if not self.path:
            self.path = default_config_path
        config_data = {}
        if os.path.exists(self.path):
            with open(self.path) as file:
                try:
                    config_data = yaml.safe_load(file)
                except Exception as e:
                    raise ValueError(f"failed to load the config file: {e}") from e
        if config_data:
            self._data = config_data

        if not self.data_dir:
            val = self._get_single_config("ARI_DATA_DIR", "data_dir", default_data_dir)
            self.data_dir = val if isinstance(val, str) else default_data_dir
        if not self.disable_default_rules:
            val = self._get_single_config(
                "ARI_DISABLE_DEFAULT_RULES", "disable_default_rules", default_disable_default_rules
            )
            self.disable_default_rules = val if isinstance(val, bool) else default_disable_default_rules
        if not self.rules_dir:
            if self.disable_default_rules:
                val = self._get_single_config("ARI_RULES_DIR", "rules_dir", "")
                self.rules_dir = val if isinstance(val, str) else ""
            else:
                val = self._get_single_config("ARI_RULES_DIR", "rules_dir", default_rules_dir)
                self.rules_dir = val if isinstance(val, str) else default_rules_dir
        # automatically add the default rules dir unless it is disabled
        if not self.rules_dir.endswith(default_rules_dir) and not self.disable_default_rules:
            self.rules_dir += ":" + default_rules_dir
        if not self.logger_key:
            val = self._get_single_config("ARI_LOGGER_KEY", "logger_key", default_logger_key)
            self.logger_key = val if isinstance(val, str) else default_logger_key
        if not self.log_level:
            val = self._get_single_config("ARI_LOG_LEVEL", "log_level", default_log_level)
            self.log_level = val if isinstance(val, str) else default_log_level
        if not self.rules:
            val = self._get_single_config("ARI_RULES", "rules", default_rules, "list", ",")
            self.rules = val if isinstance(val, list) else default_rules

    def _get_single_config(
        self,
        env_key: str = "",
        yaml_key: str = "",
        __default: str | list[str] | bool | None = None,
        __type: str | None = None,
        separator: str = "",
    ) -> str | list[str] | bool:
        """Resolve a config value from env, YAML file, or default.

        Args:
            env_key: Environment variable name to check first.
            yaml_key: Key in config YAML to check if env is not set.
            __default: Default value when neither env nor YAML has it.
            __type: If "list", split env value by separator.
            separator: String to split env value when __type is "list".

        Returns:
            The resolved value (str, list of str, or bool).
        """
        if env_key in os.environ:
            _from_env: str | list[str] | bool | None = os.environ.get(env_key, None)
            if _from_env and __type and __type == "list":
                _from_env = _from_env.split(separator) if isinstance(_from_env, str) else _from_env
            return cast(str | list[str] | bool, _from_env if _from_env is not None else __default)
        elif yaml_key in self._data:
            _from_file = self._data.get(yaml_key, None)
            return cast(str | list[str] | bool, _from_file if _from_file is not None else __default)
        else:
            return cast(str | list[str] | bool, __default)


collection_manifest_json = "MANIFEST.json"
role_meta_main_yml = "meta/main.yml"
role_meta_main_yaml = "meta/main.yaml"

supported_target_types = [
    LoadType.PROJECT,
    LoadType.COLLECTION,
    LoadType.ROLE,
    LoadType.PLAYBOOK,
]
