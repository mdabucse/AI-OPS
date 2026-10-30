from dataclasses import dataclass, field
import os


@dataclass(frozen=True)
class Settings:
    database_url: str = field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg://aiops:aiops@localhost:5433/aiops",
        )
    )
    demo_username: str = field(default_factory=lambda: os.getenv("DEMO_USERNAME", "admin"))
    demo_password: str = field(default_factory=lambda: os.getenv("DEMO_PASSWORD", "admin"))
    secret_key: str = field(default_factory=lambda: os.getenv("SECRET_KEY", "local-capstone-secret"))
    teams_webhook_url: str = field(default_factory=lambda: os.getenv("TEAMS_WEBHOOK_URL", ""))
    alert_channel: str = field(default_factory=lambda: os.getenv("ALERT_CHANNEL", "teams"))


settings = Settings()
