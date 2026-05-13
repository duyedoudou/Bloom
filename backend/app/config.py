import os
from pathlib import Path
from dotenv import load_dotenv

APP_NAME = "Bloom"


def _user_data_dir() -> Path:
    base = os.getenv("APPDATA")
    if base:
        return Path(base) / APP_NAME
    return Path.home() / f".{APP_NAME.lower()}"


USER_DATA_DIR = _user_data_dir()
USER_DATA_DIR.mkdir(parents=True, exist_ok=True)

REPO_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
USER_ENV_PATH = Path(os.getenv("BLOOM_CONFIG_PATH", USER_DATA_DIR / ".env"))

load_dotenv(REPO_ENV_PATH, override=False)
load_dotenv(USER_ENV_PATH, override=True)


def _default_database_url() -> str:
    return f"sqlite:///{(USER_DATA_DIR / 'bloom.db').as_posix()}"


class Settings:
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "qwen-plus")

    DATABASE_URL: str = os.getenv("DATABASE_URL", _default_database_url())

    CORS_ORIGINS: list[str] = [
        o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",") if o.strip()
    ]

    TESTING: bool = os.getenv("TESTING", "").lower() in ("1", "true", "yes")


settings = Settings()


def mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}...{value[-4:]}"


def _read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _write_env_file(path: Path, values: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = [
        "# LLM API (OpenAI-compatible endpoint)",
        f"LLM_API_KEY={values.get('LLM_API_KEY', '')}",
        f"LLM_BASE_URL={values.get('LLM_BASE_URL', settings.LLM_BASE_URL)}",
        f"LLM_MODEL={values.get('LLM_MODEL', settings.LLM_MODEL)}",
        "",
        "# Database",
        f"DATABASE_URL={values.get('DATABASE_URL', settings.DATABASE_URL)}",
        "",
    ]
    path.write_text("\n".join(content), encoding="utf-8")


def update_llm_settings(api_key: str | None, base_url: str, model: str) -> None:
    existing = _read_env_file(USER_ENV_PATH)
    if api_key is not None and api_key.strip():
        existing["LLM_API_KEY"] = api_key.strip()
    elif "LLM_API_KEY" not in existing:
        existing["LLM_API_KEY"] = settings.LLM_API_KEY

    existing["LLM_BASE_URL"] = base_url.strip()
    existing["LLM_MODEL"] = model.strip()
    existing.setdefault("DATABASE_URL", settings.DATABASE_URL)
    _write_env_file(USER_ENV_PATH, existing)

    settings.LLM_API_KEY = existing.get("LLM_API_KEY", "")
    settings.LLM_BASE_URL = existing["LLM_BASE_URL"]
    settings.LLM_MODEL = existing["LLM_MODEL"]
