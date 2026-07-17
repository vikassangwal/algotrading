import json
import os
import threading
from typing import Any, Dict, Optional

class ConfigManager:
    """
    A singleton class for managing system configurations.
    Loads from and saves to a local JSON file.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ConfigManager, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self, config_file: str = "system_config.json"):
        with self._lock:
            if not self._initialized:
                self.config_file = config_file
                self.config: Dict[str, Any] = {}
                self.default_config: Dict[str, Any] = {
                    "api_keys": {},
                    "slippage_thresholds": {
                        "default": 0.01
                    },
                    "risk_limits": {
                        "max_drawdown": 0.05,
                        "max_position_size": 1000.0
                    }
                }
                self.load_config()
                self._initialized = True

    def load_config(self) -> None:
        """Loads configuration from the JSON file, or uses defaults if not found."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if self.validate_config(data):
                        # Merge loaded data with defaults in case of missing keys
                        self.config = {**self.default_config, **data}
                    else:
                        print(f"Warning: Configuration in {self.config_file} is invalid. Using defaults.")
                        self.config = self.default_config.copy()
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error reading {self.config_file}: {e}. Using defaults.")
                self.config = self.default_config.copy()
        else:
            self.config = self.default_config.copy()
            self.save_config()

    def save_config(self) -> None:
        """Saves current configuration to the JSON file."""
        if self.validate_config(self.config):
            dir_name = os.path.dirname(os.path.abspath(self.config_file))
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4)
        else:
            raise ValueError("Configuration state is invalid. Cannot save.")

    def validate_config(self, config_data: Dict[str, Any]) -> bool:
        """Validates the structure and constraints of the configuration data."""
        if not isinstance(config_data, dict):
            return False

        # Validate risk limits if present
        risk = config_data.get("risk_limits")
        if risk is not None:
            if not isinstance(risk, dict):
                return False
            max_drawdown = risk.get("max_drawdown")
            if max_drawdown is not None:
                if not isinstance(max_drawdown, (int, float)) or not (0 <= max_drawdown <= 1):
                    return False
            max_position_size = risk.get("max_position_size")
            if max_position_size is not None and not isinstance(max_position_size, (int, float)):
                return False

        # Validate slippage thresholds if present
        slippage = config_data.get("slippage_thresholds")
        if slippage is not None:
            if not isinstance(slippage, dict):
                return False
            for k, v in slippage.items():
                if not isinstance(v, (int, float)):
                    return False

        return True

    def get(self, key: str, default: Any = None) -> Any:
        """Gets a configuration value by key."""
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Sets a configuration value and saves the configuration."""
        self.config[key] = value
        self.save_config()

    def get_api_key(self, service: str) -> Optional[str]:
        """Convenience method to get an API key."""
        return self.config.get("api_keys", {}).get(service)

    def set_api_key(self, service: str, key: str) -> None:
        """Convenience method to set an API key."""
        if "api_keys" not in self.config:
            self.config["api_keys"] = {}
        self.config["api_keys"][service] = key
        self.save_config()
