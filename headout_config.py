import os
from typing import Optional
from dotenv import dotenv_values


class HeadoutConfig:
    def __init__(self, env_path: str = "headout_config.env"):
        values = {}
        if os.path.exists(env_path):
            values = dotenv_values(env_path) or {}
        # Fallback to process env
        proc = {
            k: os.getenv(k) for k in [
                "HEADOUT_EMAIL",
                "HEADOUT_PASSWORD",
                "BROWSER_ENGINE",
                "BROWSER_CHANNEL",
                "BROWSER_HEADLESS",
                "BROWSER_PERSISTENT",
                "BROWSER_USER_DATA_DIR",
                "BROWSER_STORAGE_STATE",
                "DATABASE_PATH",
                "AIRTABLE_API_KEY",
                "AIRTABLE_BASE_ID",
                "AIRTABLE_TABLE",
                "HEADOUT_LOGIN_URL",
                "HEADOUT_PORTAL_URL",
                "LOG_FILE",
                "LOG_LEVEL",
                "RUN_AIRTABLE_TESTS",
                "CSV_PATH"
            ]
        }
        for k, v in proc.items():
            if v is not None and k not in values:
                values[k] = v

        self.values = values

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        return self.values.get(key, default)

    @property
    def email(self) -> Optional[str]:
        return self.get("HEADOUT_EMAIL")

    @property
    def password(self) -> Optional[str]:
        return self.get("HEADOUT_PASSWORD")

    @property
    def browser_engine(self) -> str:
        return self.get("BROWSER_ENGINE", "chromium")

    @property
    def browser_channel(self) -> Optional[str]:
        return self.get("BROWSER_CHANNEL")

    @property
    def headless(self) -> bool:
        v = self.get("BROWSER_HEADLESS", "false").lower()
        return v in ("1", "true", "yes")

    @property
    def persistent(self) -> bool:
        v = self.get("BROWSER_PERSISTENT", "true").lower()
        return v in ("1", "true", "yes")

    @property
    def user_data_dir(self) -> str:
        return self.get("BROWSER_USER_DATA_DIR", "./headout_browser_profile")

    @property
    def storage_state_path(self) -> str:
        return self.get("BROWSER_STORAGE_STATE", "./headout_session.json")

    @property
    def login_url(self) -> Optional[str]:
        return self.get("HEADOUT_LOGIN_URL")

    @property
    def portal_url(self) -> Optional[str]:
        return self.get("HEADOUT_PORTAL_URL")

    @property
    def csv_path(self) -> Optional[str]:
        return self.get("CSV_PATH")

