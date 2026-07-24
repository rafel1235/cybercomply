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

    @property
    def supabase_admin_configured(self) -> bool:
        """Serve solo per la cancellazione account (GDPR Art. 17, Fase 8): la Admin API
        di Supabase Auth richiede la service role key, non l'anon key usata dal resto
        dell'app. Come per Stripe/Resend/cifratura, i valori segnaposto di `.env.example`
        (mai sostituiti con credenziali reali in questa sessione) non contano come
        configurati, altrimenti si tenterebbe una vera chiamata HTTP verso un URL finto.
        """
        return (
            bool(self.supabase_url)
            and not self.supabase_url.startswith("https://YOUR-PROJECT")
            and bool(self.supabase_service_role_key)
            and not self.supabase_service_role_key.startswith("replace-with")
        )

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

    # --- Resend (Fase 7 — email transazionali) ---
    resend_api_key: str = ""
    # Deve corrispondere a un dominio verificato (SPF/DKIM/DMARC) sul progetto Resend
    # prima del lancio commerciale — vedi nota in .env.example.
    email_from_address: str = "CyberComplyIT <noreply@cybercomplyit.it>"

    @property
    def email_configured(self) -> bool:
        return bool(self.resend_api_key) and not self.resend_api_key.startswith(
            "replace-with"
        )

    # --- Cifratura campi sensibili a riposo (Fase 8) ---
    # Chiave Fernet (32 byte urlsafe-base64): generarne una reale con
    # `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.
    # ATTENZIONE: perdere questa chiave rende illeggibili per sempre i dati già cifrati
    # con essa — conservarla con la stessa cura di una password di database, mai nel repo.
    field_encryption_key: str = ""

    @property
    def field_encryption_configured(self) -> bool:
        return bool(
            self.field_encryption_key
        ) and not self.field_encryption_key.startswith("replace-with")

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
