from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    allowed_origins: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    app_name: str = "Attendance Management API"
    debug: bool = True

    class Config:
        env_file = ".env"


settings = Settings()
