from sqlalchemy import text
from sqlalchemy.engine import Engine


def ensure_schema_compatibility(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ;
                """
            )
        )
        connection.execute(
            text(
                """
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS last_logout_at TIMESTAMPTZ;
                """
            )
        )
        connection.execute(
            text(
                """
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS last_interaction_at TIMESTAMPTZ;
                """
            )
        )
        connection.execute(
            text(
                """
                ALTER TABLE runtime_settings
                ADD COLUMN IF NOT EXISTS outbound_auth_type VARCHAR(20) NOT NULL DEFAULT 'none';
                """
            )
        )
        connection.execute(
            text(
                """
                ALTER TABLE runtime_settings
                ADD COLUMN IF NOT EXISTS outbound_auth_header_name VARCHAR(100);
                """
            )
        )
        connection.execute(
            text(
                """
                ALTER TABLE runtime_settings
                ADD COLUMN IF NOT EXISTS outbound_auth_header_value VARCHAR(1000);
                """
            )
        )
        connection.execute(
            text(
                """
                ALTER TABLE runtime_settings
                ADD COLUMN IF NOT EXISTS outbound_auth_basic_username VARCHAR(255);
                """
            )
        )
        connection.execute(
            text(
                """
                ALTER TABLE runtime_settings
                ADD COLUMN IF NOT EXISTS outbound_auth_basic_password VARCHAR(1000);
                """
            )
        )
        connection.execute(
            text(
                """
                ALTER TABLE runtime_settings
                ADD COLUMN IF NOT EXISTS outbound_auth_jwt_token VARCHAR(2000);
                """
            )
        )
        connection.execute(
            text(
                """
                ALTER TABLE conversations
                ADD COLUMN IF NOT EXISTS profile_picture_url VARCHAR(1000);
                """
            )
        )
        connection.execute(
            text(
                """
                ALTER TABLE runtime_settings
                ADD COLUMN IF NOT EXISTS ai_provider VARCHAR(50) NOT NULL DEFAULT 'gemini',
                ADD COLUMN IF NOT EXISTS ai_api_key VARCHAR(500),
                ADD COLUMN IF NOT EXISTS ai_base_url VARCHAR(500) DEFAULT 'https://ollama.sti.ufpb.br/',
                ADD COLUMN IF NOT EXISTS ai_model VARCHAR(100);
                """
            )
        )
