import configparser
from pathlib import Path
import os


def fetch_config_value(config_filename: str, value_name: str) -> str:
    """Fetch one string value from a ConfigParser-style config file.

    ``value_name`` should usually use ``section.option`` format, for example
    ``redis.default_schema_key_prefix``.
    """
    parser = configparser.ConfigParser()
    config_path = Path(config_filename)
    if not config_path.is_absolute() and not config_path.exists():
        config_path = Path(__file__).with_name(config_filename)

    if not parser.read(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")

    if "." in value_name:
        section, option = value_name.split(".", 1)
        if parser.has_option(section, option):
            return parser.get(section, option).strip()
        raise KeyError(f"Config value not found: {section}.{option}")

    if parser.has_option(configparser.DEFAULTSECT, value_name):
        return parser.get(configparser.DEFAULTSECT, value_name).strip()

    matching_sections = [section for section in parser.sections() if parser.has_option(section, value_name)]
    if len(matching_sections) == 1:
        return parser.get(matching_sections[0], value_name).strip()
    if len(matching_sections) > 1:
        raise KeyError(f"Config value name is ambiguous: {value_name}")

    raise KeyError(f"Config value not found: {value_name}")


def load_api_key(env_var_name: str) -> str:
    """Load the API key from the environment."""
    api_key = os.getenv(env_var_name, "").strip()
    if api_key:
        return api_key

    raise ValueError(f"jAPI key not found in environment variable {env_var_name}.")
