from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://veeam:changeme@localhost:5432/veeam_audit"
    reports_dir: str = "./reports"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
