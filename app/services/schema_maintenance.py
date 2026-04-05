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
