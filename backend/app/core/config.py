from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://arenah:arenah_pwd@localhost:5432/arenah"
    secret_key: str = "cle-de-developpement-arenah-a-changer-en-production"
    access_token_expire_minutes: int = 60 * 10  # 10 heures (une journée de travail)
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    admin_password: str = "Admin@2026"           # mot de passe initial du compte admin (import)
    mot_de_passe_provisoire: str = "Arenah@2026"  # mot de passe initial des employés (import)
    fuseau_horaire: str = "Indian/Antananarivo"   # heures affichées et enregistrées à l'heure de Madagascar

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
