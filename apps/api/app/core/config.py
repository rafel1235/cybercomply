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
    # Modello usato per la generazione documenti (Fase 5). Aggiornabile da .env senza
    # toccare il codice quando Anthropic rilascia nuove versioni.
    anthropic_model: str = "claude-sonnet-5"
    # Costo stimato per monitoraggio spesa (Fase 5, roadmap: "costo stimato" per chiamata).
    # Lasciati a 0 di default: vanno impostati in .env con i prezzi reali correnti dalla
    # pagina pricing di Anthropic, per non registrare una stima basata su cifre non
    # verificate. A 0, il log della chiamata riporta i token ma non un costo in USD.
    anthropic_input_cost_per_mtok: float = 0.0
    anthropic_output_cost_per_mtok: float = 0.0

    # Storage locale dei PDF generati, in attesa dell'integrazione con Supabase Storage
    # (Fase 5/6). Directory ignorata da git (vedi .gitignore) perché contiene solo output
    # rigenerabile, non sorgenti.
    local_storage_dir: str = "storage"

    # --- Stripe (Fase 6 — pagamenti e piani) ---
    stripe_secret_key: str = ""
    stripe_publishable_key: str = ""
    # Segreto per verificare la firma dei webhook Stripe (obbligatorio in produzione:
    # senza verifica, chiunque potrebbe fingere di essere Stripe e attivare piani gratis).
    stripe_webhook_secret: str = ""
    # ID dei prezzi ricorrenti creati sulla dashboard Stripe. Enterprise non ha un prezzo
    # self-service (roadmap: "Enterprise (contattaci)"), quindi non serve un price id qui.
    stripe_price_id_essential: str = ""
    stripe_price_id_business: str = ""
    # Base per le redirect URL di Checkout/Billing Portal.
    frontend_base_url: str = "http://localhost:3000"

    @property
    def stripe_configured(self) -> bool:
        return bool(self.stripe_secret_key) and not self.stripe_secret_key.startswith(
            "replace-with"
        )

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
