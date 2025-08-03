"""Configuration management for tvmux."""
import os
import sys
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

# Handle tomllib import for Python 3.10
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


class OutputConfig(BaseModel):
    """Output configuration."""
    directory: str = Field(default="~/Videos/tmux", description="Base directory for recordings")
    date_format: str = Field(default="%Y-%m", description="Date format for subdirectories")


class ServerConfig(BaseModel):
    """Server configuration."""
    port: int = Field(default=21590, description="Server port")
    auto_start: bool = Field(default=True, description="Auto-start server when needed")
    auto_shutdown: bool = Field(default=True, description="Auto-shutdown when no recordings")


class RecordingConfig(BaseModel):
    """Recording configuration."""
    repair_on_stop: bool = Field(default=True, description="Repair cast files on stop")
    follow_active_pane: bool = Field(default=True, description="Follow active pane switches")


class AnnotationConfig(BaseModel):
    """Annotation configuration."""
    include_cursor_state: bool = Field(default=True, description="Include cursor position/visibility")


class Config(BaseModel):
    """Main tvmux configuration."""
    output: OutputConfig = Field(default_factory=OutputConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    recording: RecordingConfig = Field(default_factory=RecordingConfig)
    annotations: AnnotationConfig = Field(default_factory=AnnotationConfig)


def load_config(config_file: Optional[str] = None) -> Config:
    """Load configuration from file and environment variables.

    Precedence (highest to lowest):
    1. Environment variables
    2. Specified config file
    3. TVMUX_CONFIG_FILE environment variable
    4. ~/.tvmux.conf
    5. Built-in defaults
    """
    config_data = {}

    # Find config file
    if config_file:
        config_path = Path(config_file).expanduser()
    elif os.getenv("TVMUX_CONFIG_FILE"):
        config_path = Path(os.getenv("TVMUX_CONFIG_FILE")).expanduser()
    else:
        config_path = Path.home() / ".tvmux.conf"

    # Load from file if it exists
    if config_path.exists():
        with open(config_path, "rb") as f:
            config_data = tomllib.load(f)

    # Apply environment variable overrides
    env_overrides = {}

    # Output overrides
    if os.getenv("TVMUX_OUTPUT_DIR"):
        env_overrides.setdefault("output", {})["directory"] = os.getenv("TVMUX_OUTPUT_DIR")

    # Server overrides
    if os.getenv("TVMUX_SERVER_PORT"):
        env_overrides.setdefault("server", {})["port"] = int(os.getenv("TVMUX_SERVER_PORT"))

    if os.getenv("TVMUX_AUTO_START"):
        env_overrides.setdefault("server", {})["auto_start"] = os.getenv("TVMUX_AUTO_START").lower() in ("true", "1", "yes")

    # Merge environment overrides into config data
    for section, values in env_overrides.items():
        config_data.setdefault(section, {}).update(values)

    # Create and return config object
    return Config(**config_data)


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def set_config(config: Config) -> None:
    """Set the global configuration instance."""
    global _config
    _config = config
