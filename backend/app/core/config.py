from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Default points at the isolated dev container from docker-compose.dev.yml.
    # Never default to a shared/system Postgres: it could be another project's DB.
    DATABASE_URL: str = "postgresql://church_saas:church_saas_dev@localhost:55440/church_saas"
    SECRET_KEY: str = "change-this-secret"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Comma-separated list of browser origins (Vercel preview + production, local dev)
    # Example: https://church-cms.vercel.app,https://church-cms-git-main-org.vercel.app,http://localhost:5173
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""

    SENDGRID_API_KEY: str = ""
    FROM_EMAIL: str = "noreply@livingsspring.org"

    SMS_PROVIDER: str = "arkesel"

    ARKESEL_API_KEY: str = ""
    ARKESEL_SENDER_ID: str = "LivingSpring"
    ARKESEL_BASE_URL: str = "https://sms.arkesel.com"

    MOOLRE_VAS_KEY: str = ""
    MOOLRE_SENDER_ID: str = "LivingSpring"
    MOOLRE_BASE_URL: str = "https://api.moolre.com"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("DATABASE_URL")
    @classmethod
    def _use_psycopg2_driver(cls, value: str) -> str:
        """Pin the driver to psycopg2 (the one in requirements.txt).

        SQLAlchemy 2.1 changed a bare ``postgresql://`` URL to mean psycopg v3,
        which is not installed. Hosted providers (Render, Supabase) hand out bare
        ``postgresql://`` or legacy ``postgres://`` URLs, so normalise them here.
        URLs that already name a driver (``postgresql+...``) are left untouched.
        """
        for prefix in ("postgres://", "postgresql://"):
            if value.startswith(prefix):
                return "postgresql+psycopg2://" + value[len(prefix):]
        return value


settings = Settings()
