from sqlalchemy import create_engine, text
from app.core.config import get_settings

def migrate():
    settings = get_settings()
    # Connect with AUTOCOMMIT so we can alter types
    engine = create_engine(settings.database_url, isolation_level="AUTOCOMMIT")
    
    with engine.connect() as conn:
        print("Migrating delivery_status ENUM...")
        try:
            conn.execute(text("ALTER TYPE delivery_status ADD VALUE 'delivered'"))
            print("Added 'delivered' to delivery_status.")
        except Exception as e:
            if "already exists" in str(e):
                print("'delivered' already exists.")
            else:
                print(f"Error adding 'delivered': {e}")
                
        try:
            conn.execute(text("ALTER TYPE delivery_status ADD VALUE 'read'"))
            print("Added 'read' to delivery_status.")
        except Exception as e:
            if "already exists" in str(e):
                print("'read' already exists.")
            else:
                print(f"Error adding 'read': {e}")
                
        print("Migration finished successfully.")

if __name__ == "__main__":
    migrate()
