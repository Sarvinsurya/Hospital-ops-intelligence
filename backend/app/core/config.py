"""Central configuration for the Hospital Operations Intelligence backend."""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]  # .../backend
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
WAREHOUSE_DIR = DATA_DIR / "warehouse"
MODELS_DIR = DATA_DIR / "models"
DB_PATH = WAREHOUSE_DIR / "hospital_ops.db"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Hospital Operations Intelligence System"
    api_prefix: str = "/api"

    # Ollama (local LLM) config
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:3b"
    agent_max_tool_calls: int = 6

    # Operational thresholds that drive anomaly detection & agent triggers
    occupancy_critical: float = 0.90   # 90% bed occupancy -> critical
    occupancy_warning: float = 0.80    # 80% -> warning
    wait_time_critical_min: float = 60.0   # minutes
    wait_time_warning_min: float = 40.0
    nurse_ratio_danger: float = 8.0    # patients per nurse considered unsafe
    surge_lookahead_hours: int = 4

    db_path: str = str(DB_PATH)


settings = Settings()
