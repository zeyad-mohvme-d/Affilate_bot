"""
Config loader with environment-variable overrides.

Loads config.json from the project root, then lets these env vars override
sensitive fields (used by GitHub Actions via repository secrets):

    TELEGRAM_BOT_TOKEN     -> telegram.bot_token
    TELEGRAM_CHANNEL_ID    -> telegram.channel_id
    PINTEREST_EMAIL        -> pinterest.email
    PINTEREST_PASSWORD     -> pinterest.password

All other code in the project should import `load_config` from here,
NOT read config.json directly.
"""

import json
import os
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"

ENV_OVERRIDES = {
    ("telegram", "bot_token"): "TELEGRAM_BOT_TOKEN",
    ("telegram", "channel_id"): "TELEGRAM_CHANNEL_ID",
    ("pinterest", "email"): "PINTEREST_EMAIL",
    ("pinterest", "password"): "PINTEREST_PASSWORD",
}


def load_config() -> dict:
    """Return config dict, with env-var overrides applied where set."""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

    for (section, key), env_name in ENV_OVERRIDES.items():
        value = os.environ.get(env_name)
        if value:
            config.setdefault(section, {})[key] = value

    return config
