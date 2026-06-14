"""
Config loader — reads YAML config and resolves ${ENV_VAR} patterns.
This is the FIRST utility file main.py uses at startup.
"""
import os
from pathlib import Path
from typing import Any, Dict
import yaml
from dotenv import load_dotenv

# Load .env file if present (development convenience)
load_dotenv()


def load_config(path: str = "configs/config.yaml") -> Dict[str, Any]:
    """
    Load YAML config file with environment variable substitution.
    
    Args:
        path: Path to YAML config file
    
    Returns:
        Dict containing all configuration values
    
    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If YAML is malformed
    
    Example:
        >>> config = load_config("configs/config.yaml")
        >>> config["system"]["mode"]
        'paper'
        >>> config["guardrails"]["max_drawdown_pct"]
        0.15
    """
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(
            f"Config file not found: {path}\n"
            f"Current working directory: {os.getcwd()}\n"
            f"Expected location: {config_path.absolute()}"
        )
    
    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    
    # Recursively resolve ${ENV_VAR} patterns
    config = _resolve_env_vars(raw)
    return config


def _resolve_env_vars(obj: Any) -> Any:
    """
    Recursively walk through config and replace ${ENV_VAR} with actual values.
    
    Examples:
        "paper" → "paper" (no change)
        "${TELEGRAM_BOT_TOKEN}" → actual token from env
        ["BTC/USDT", "${CUSTOM_SYMBOL}"] → resolved list
    """
    if isinstance(obj, str):
        if obj.startswith("${") and obj.endswith("}"):
            env_key = obj[2:-1]
            env_value = os.getenv(env_key)
            if env_value is None:
                # Keep the placeholder if env var not set
                return obj
            return env_value
        return obj
    elif isinstance(obj, dict):
        return {k: _resolve_env_vars(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_resolve_env_vars(v) for v in obj]
    return obj


def get(config: Dict, dotted_key: str, default: Any = None) -> Any:
    """
    Get nested config value via dotted key notation.
    
    Args:
        config: The config dict
        dotted_key: Dot-separated path like 'owner.review_interval_minutes'
        default: Default value if key not found
    
    Returns:
        Value at that path, or default
    
    Example:
        >>> get(config, "system.mode")
        'paper'
        >>> get(config, "owner.review_interval_minutes")
        60
        >>> get(config, "nonexistent.key", "default")
        'default'
    """
    keys = dotted_key.split(".")
    val = config
    for k in keys:
        if isinstance(val, dict) and k in val:
            val = val[k]
        else:
            return default
    return val


def merge_configs(base: Dict, override: Dict) -> Dict:
    """
    Deep merge two configs. Override takes precedence.
    Useful for: base config + user-specific overrides.
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_configs(result[key], value)
        else:
            result[key] = value
    return result


def validate_config(config: Dict) -> list:
    """
    Validate critical config values. Returns list of errors.
    Empty list = valid.
    """
    errors = []
    
    # System mode
    mode = config.get("system", {}).get("mode")
    if mode not in ("paper", "live", "backtest"):
        errors.append(f"Invalid system.mode: {mode} (must be paper|live|backtest)")
    
    # Guardrails
    guardrails = config.get("guardrails", {})
    if guardrails.get("max_drawdown_pct", 0) > 0.5:
        errors.append("max_drawdown_pct > 50% is dangerous")
    if guardrails.get("position_size_max_pct", 0) > 0.10:
        errors.append("position_size_max_pct > 10% is dangerous")
    
    # Data sources
    crypto = config.get("data", {}).get("crypto", {})
    if not crypto.get("symbols"):
        errors.append("No crypto symbols configured")
    forex = config.get("data", {}).get("forex", {})
    if not forex.get("symbols"):
        errors.append("No forex symbols configured")
    
    # Owner
    owner = config.get("owner", {})
    if owner.get("review_interval_minutes", 0) < 1:
        errors.append("review_interval_minutes must be >= 1")
    
    return errors
