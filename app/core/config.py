import os
from dotenv import load_dotenv


load_dotenv()

def _require(name:str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment var: {name}")
    return value

def _get_int_env(name: str, default: str) -> int:
    value = os.getenv(name, default)
    try:
        return int(value)
    except ValueError:
        raise RuntimeError(f"Environment variable {value} must be an integer")


def _get_env(name: str, default: str) -> str:
    value = os.getenv(name, default)
    return value

class Settings:
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    ALGORITHM: str

    def __init__(self):
        self.POSTGRES_USER = _require("POSTGRES_USER")
        self.POSTGRES_PASSWORD = _require("POSTGRES_PASSWORD")
        self.POSTGRES_DB = _get_env("POSTGRES_DB", "taskflow")
        self.POSTGRES_HOST = _get_env("POSTGRES_HOST", "localhost")
        self.POSTGRES_PORT = _get_int_env("POSTGRES_PORT", "5432")
        self.SECRET_KEY = _require("SECRET_KEY")
        self.ACCESS_TOKEN_EXPIRE_MINUTES = _get_int_env("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
        self.ALGORITHM = _get_env("ALGORITHM", "HS256")

    @property
    def db_url(self) -> str:
        return (f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}")

    @property
    def sync_db_url(self) -> str:
        return (f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}")


settings = Settings()
