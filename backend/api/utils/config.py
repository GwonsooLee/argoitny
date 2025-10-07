"""Configuration Management Utility

This module handles loading configuration from YAML files or environment variables.
Supports Kubernetes ConfigMap integration.

Usage:
    from api.utils.config import ConfigLoader

    config = ConfigLoader.load()
    db_host = config.get('database.host')
    redis_enabled = config.get('cache.enable_redis', default=False)
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Loads configuration from YAML files with environment variable fallback"""

    _config_cache: Optional[Dict[str, Any]] = None
    _config_path: Optional[Path] = None

    @classmethod
    def load(cls, config_path: Optional[str] = None, reload: bool = False) -> 'ConfigLoader':
        """
        Load configuration from file or cache

        Args:
            config_path: Path to configuration file. If None, uses CONFIG_FILE env var
                        or defaults to config/config.yaml
            reload: Force reload even if cached

        Returns:
            ConfigLoader instance
        """
        if cls._config_cache is not None and not reload:
            return cls()

        # Determine config file path
        if config_path:
            cls._config_path = Path(config_path)
        elif os.getenv('CONFIG_FILE'):
            cls._config_path = Path(os.getenv('CONFIG_FILE'))
        else:
            # Default paths to check
            base_dir = Path(__file__).resolve().parent.parent.parent
            default_paths = [
                base_dir / 'config' / 'config.yaml',
                base_dir / 'config.yaml',
                Path('/etc/algoitny/config.yaml'),  # Kubernetes ConfigMap mount point
            ]

            for path in default_paths:
                if path.exists():
                    cls._config_path = path
                    break

        # Load configuration
        if cls._config_path and cls._config_path.exists():
            logger.info(f"Loading configuration from: {cls._config_path}")
            cls._config_cache = cls._load_yaml(cls._config_path)
        else:
            logger.warning(f"Configuration file not found. Using environment variables only.")
            cls._config_cache = {}

        return cls()

    @staticmethod
    def _load_yaml(path: Path) -> Dict[str, Any]:
        """Load YAML file"""
        try:
            with open(path, 'r') as f:
                config = yaml.safe_load(f) or {}
                logger.info(f"Successfully loaded configuration from {path}")
                return config
        except Exception as e:
            logger.error(f"Error loading configuration from {path}: {e}")
            return {}

    @classmethod
    def get(cls, key: str, default: Any = None, env_var: Optional[str] = None) -> Any:
        """
        Get configuration value with fallback chain:
        1. Environment variable (if env_var specified)
        2. Configuration file
        3. Default value

        Args:
            key: Dot-separated key (e.g., 'database.host')
            default: Default value if not found
            env_var: Environment variable name to check first

        Returns:
            Configuration value

        Example:
            config.get('database.host', default='localhost', env_var='DB_HOST')
        """
        # Ensure config is loaded
        if cls._config_cache is None:
            cls.load()

        # Check environment variable first
        if env_var and os.getenv(env_var):
            value = os.getenv(env_var)
            # Convert string booleans
            if value.lower() in ('true', 'false'):
                return value.lower() == 'true'
            # Convert string numbers
            try:
                if '.' in value:
                    return float(value)
                return int(value)
            except ValueError:
                pass
            return value

        # Check configuration file
        keys = key.split('.')
        value = cls._config_cache

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value if value is not None else default

    @classmethod
    def get_bool(cls, key: str, default: bool = False, env_var: Optional[str] = None) -> bool:
        """Get boolean configuration value"""
        value = cls.get(key, default=default, env_var=env_var)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        return bool(value)

    @classmethod
    def get_int(cls, key: str, default: int = 0, env_var: Optional[str] = None) -> int:
        """Get integer configuration value"""
        value = cls.get(key, default=default, env_var=env_var)
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    @classmethod
    def get_float(cls, key: str, default: float = 0.0, env_var: Optional[str] = None) -> float:
        """Get float configuration value"""
        value = cls.get(key, default=default, env_var=env_var)
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    @classmethod
    def get_list(cls, key: str, default: list = None, env_var: Optional[str] = None, separator: str = ',') -> list:
        """
        Get list configuration value

        If from env var, splits by separator (default: comma)
        """
        if default is None:
            default = []

        value = cls.get(key, default=default, env_var=env_var)

        if isinstance(value, list):
            return value
        if isinstance(value, str):
            return [item.strip() for item in value.split(separator) if item.strip()]

        return default

    @classmethod
    def get_dict(cls, key: str, default: dict = None) -> dict:
        """Get dictionary configuration value"""
        if default is None:
            default = {}

        value = cls.get(key, default=default)
        return value if isinstance(value, dict) else default

    @classmethod
    def reload(cls):
        """Force reload configuration"""
        cls._config_cache = None
        return cls.load(reload=True)

    @classmethod
    def get_all(cls) -> Dict[str, Any]:
        """Get all configuration"""
        if cls._config_cache is None:
            cls.load()
        return cls._config_cache.copy()

    @classmethod
    def set(cls, key: str, value: Any):
        """
        Set configuration value (runtime only, not persisted)
        Useful for testing
        """
        if cls._config_cache is None:
            cls.load()

        keys = key.split('.')
        config = cls._config_cache

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value

    @classmethod
    def clear(cls):
        """Clear cached configuration (useful for testing)"""
        cls._config_cache = None
        cls._config_path = None


# Convenience instance
config = ConfigLoader.load()
