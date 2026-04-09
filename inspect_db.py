from app.core.config import get_settings
from sqlalchemy import create_engine, text

engine = create_engine(get_settings().database_url)
with engine.connect() as conn:
    res = conn.execute(text("SELECT id, contact_phone, contact_name FROM conversations WHERE contact_phone = '+558332167336'"))
    for row in res:
        print(f"Conversation: {row}")
        
    print("-- Messages --")
    res2 = conn.execute(text("SELECT id, sender_phone, direction, raw_payload FROM messages WHERE conversation_id IN (SELECT id FROM conversations WHERE contact_phone = '+558332167336') ORDER BY id DESC LIMIT 5"))
    for row in res2:
        print(f"Msg {row.id} - Dir {row.direction} - Phone {row.sender_phone}")
        import json
        try:
            print(json.dumps(row.raw_payload, indent=2))
        except:
            print(row.raw_payload)
