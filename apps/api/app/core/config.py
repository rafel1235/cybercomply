"""Configurazione centralizzata dell'app, letta da variabili d'ambiente.

Nessun segreto è hardcoded: tutti i valori sensibili arrivano da `.env` (mai committato,
vedi .gitignore) e in produzione da variabili d'ambiente iniettate dall'hosting.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_API_ROOT = Path(__file__).resolve().parents[2]  # apps/api/


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    api_v1_prefix: str = "/api/v1"
    allowed_origins: str = "http://localhost:3000"

    database_url: str = (
        "postgresql+psycopg2://postgres:postgres@localhost:5432/cybercomplyit"
    )

    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""

    login_rate_limit: str = "10/15minutes"

    anthropic_api_key: str = ""

    # Storage locale dei PDF generati, in attesa dell'integrazione con Supabase Storage
    # (Fase 5/6). Directory ignorata da git (vedi .gitignore) perché contiene solo output
    # rigenerabile, non sorgenti.
    local_storage_dir: str = "storage"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def local_storage_path(self) -> Path:
        path = _API_ROOT / self.local_storage_dir
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache
def get_settings() -> Settings:
    return Settings()
