"""Fix contacts with name 'Você' by extracting real names from inbound messages."""
import sys
sys.path.insert(0, "/app")

from app.db.session import SessionLocal
from app.models.conversation import Conversation
from app.models.message import Message, MessageDirection


def fix():
    db = SessionLocal()
    convs = db.query(Conversation).filter(Conversation.contact_name == "Você").all()
    print(f"Found {len(convs)} conversations with name 'Você'")

    fixed = 0
    for conv in convs:
        # Get most recent inbound message
        msg = db.query(Message).filter(
            Message.conversation_id == conv.id,
            Message.direction == MessageDirection.INBOUND,
        ).order_by(Message.created_at.desc()).first()

        real_name = None

        # Try pushName from raw_payload
        if msg and msg.raw_payload:
            raw = msg.raw_payload
            root = raw.get("data") or raw.get("body", {}).get("data") or raw
            real_name = root.get("pushName") or root.get("notify")

        # Fallback: sender_name from message (for inbound, this is the contact name)
        if not real_name or real_name == "Você":
            if msg and msg.sender_name and msg.sender_name != "Você":
                real_name = msg.sender_name

        if real_name and real_name != "Você":
            print(f"  {conv.contact_phone}: Você -> {real_name}")
            conv.contact_name = real_name
            fixed += 1
        else:
            print(f"  {conv.contact_phone}: No real name found, clearing name")
            conv.contact_name = None
            fixed += 1

    db.commit()
    db.close()
    print(f"Fixed {fixed} contacts")


if __name__ == "__main__":
    fix()
